"""ElevenLabs TTS Provider - Premium cloud TTS with voice cloning"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional

from jarvis.core.tts_engine import TTSEngine


class ElevenLabsProvider(TTSEngine):
    """
    ElevenLabs cloud TTS provider.
    
    Features:
    - Ultra-realistic voice synthesis
    - Voice cloning capability
    - Streaming support for low latency
    - Multiple voice options
    
    Requires API key ($5-20/month).
    """
    
    def __init__(
        self,
        api_key: str,
        voice: str = "Daniel",  # British male, JARVIS-like
        model: str = "eleven_monolingual_v1",
    ):
        self.api_key = api_key
        self.voice = voice
        self.model = model
        self._client = None
        self._voices_cache: Optional[Dict] = None
    
    def _ensure_client(self):
        """Lazy initialization of ElevenLabs client"""
        if self._client is None:
            try:
                import elevenlabs
                elevenlabs.set_api_key(self.api_key)
                self._client = elevenlabs
            except ImportError:
                raise ImportError(
                    "ElevenLabs package not installed. "
                    "Install with: pip install elevenlabs"
                )
    
    async def speak(self, text: str) -> None:
        """Generate and play speech"""
        self._ensure_client()
        
        # Run in thread pool since elevenlabs is sync
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._speak_sync, text)
    
    def _speak_sync(self, text: str) -> None:
        """Synchronous speak implementation"""
        audio = self._client.generate(
            text=text,
            voice=self.voice,
            model=self.model,
        )
        self._client.play(audio)
    
    async def synthesize(self, text: str) -> bytes:
        """Generate speech and return audio bytes"""
        self._ensure_client()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._synthesize_sync, text)
    
    def _synthesize_sync(self, text: str) -> bytes:
        """Synchronous synthesize implementation"""
        audio = self._client.generate(
            text=text,
            voice=self.voice,
            model=self.model,
        )
        return b"".join(audio) if hasattr(audio, "__iter__") else audio
    
    async def save(self, text: str, output_path: Path) -> None:
        """Generate speech and save to file"""
        audio_bytes = await self.synthesize(text)
        Path(output_path).write_bytes(audio_bytes)
    
    async def speak_stream(self, text_stream: AsyncIterator[str]) -> None:
        """
        Stream audio output as text arrives.
        
        ElevenLabs supports true streaming for ~100ms latency.
        """
        self._ensure_client()
        
        # Collect text chunks
        text_chunks = []
        async for chunk in text_stream:
            text_chunks.append(chunk)
        
        full_text = "".join(text_chunks)
        
        # Use streaming API
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._stream_sync, full_text)
    
    def _stream_sync(self, text: str) -> None:
        """Synchronous streaming implementation"""
        audio = self._client.generate(
            text=text,
            voice=self.voice,
            model=self.model,
            stream=True,
        )
        self._client.stream(audio)
    
    def get_available_voices(self) -> List[str]:
        """List available ElevenLabs voices"""
        self._ensure_client()
        
        if self._voices_cache is None:
            try:
                voices = self._client.voices()
                self._voices_cache = {v.name: v.voice_id for v in voices}
            except Exception:
                return ["Daniel", "Rachel", "Adam", "Bella"]
        
        return list(self._voices_cache.keys())
    
    async def health_check(self) -> bool:
        """Check if ElevenLabs API is accessible"""
        try:
            self._ensure_client()
            # Try to list voices as health check
            voices = self._client.voices()
            return len(voices) > 0
        except Exception:
            return False
