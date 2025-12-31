"""Whisper STT Provider - Local speech recognition using faster-whisper"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncIterator, List, Optional

from jarvis.core.stt_engine import STTEngine, TranscriptionResult


class WhisperProvider(STTEngine):
    """
    Local speech-to-text using faster-whisper (CTranslate2 optimized).
    
    Features:
    - 4x faster than OpenAI Whisper
    - Runs entirely on-device (M4 optimized)
    - Multiple model sizes available
    - Multilingual support
    
    Model sizes:
    - tiny: ~39M params, fastest
    - base: ~74M params
    - small: ~244M params
    - medium: ~769M params
    - large-v3: ~1.5B params, most accurate
    - large-v3-turbo: ~800M params, balanced
    """
    
    def __init__(
        self,
        model_size: str = "large-v3-turbo",
        language: str = "en",
        device: str = "auto",
        compute_type: str = "auto",
    ):
        self.model_size = model_size
        self.language = language
        self.device = device
        self.compute_type = compute_type
        self._model = None
    
    def _ensure_model(self):
        """Lazy load the Whisper model"""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                )
            except ImportError:
                raise ImportError(
                    "faster-whisper not installed. "
                    "Install with: pip install faster-whisper"
                )
    
    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """Transcribe audio from file"""
        self._ensure_model()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._transcribe_sync, str(audio_path)
        )
    
    def _transcribe_sync(self, audio_path: str) -> TranscriptionResult:
        """Synchronous transcription"""
        segments, info = self._model.transcribe(
            audio_path,
            language=self.language,
            beam_size=5,
            vad_filter=True,  # Filter out silence
            vad_parameters=dict(
                min_silence_duration_ms=500,
            ),
        )
        
        # Collect all segment text
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())
        
        full_text = " ".join(text_parts)
        
        return TranscriptionResult(
            text=full_text,
            language=info.language,
            confidence=info.language_probability,
            duration_seconds=info.duration,
        )
    
    async def transcribe_bytes(self, audio_bytes: bytes) -> TranscriptionResult:
        """Transcribe from raw audio bytes"""
        # Save to temp file and transcribe
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = Path(f.name)
        
        try:
            return await self.transcribe(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)
    
    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[str]:
        """
        Real-time streaming transcription.
        
        For now, buffers audio and transcribes.
        True streaming would require VAD + chunked inference.
        """
        # Collect audio chunks
        chunks = []
        async for chunk in audio_stream:
            chunks.append(chunk)
        
        if not chunks:
            return
        
        # Combine and transcribe
        audio_bytes = b"".join(chunks)
        result = await self.transcribe_bytes(audio_bytes)
        yield result.text
    
    async def health_check(self) -> bool:
        """Check if Whisper can be loaded"""
        try:
            self._ensure_model()
            return self._model is not None
        except Exception:
            return False
    
    def get_available_models(self) -> List[str]:
        """List available Whisper model sizes"""
        return [
            "tiny",
            "tiny.en",
            "base",
            "base.en",
            "small",
            "small.en",
            "medium",
            "medium.en",
            "large-v1",
            "large-v2",
            "large-v3",
            "large-v3-turbo",
        ]
