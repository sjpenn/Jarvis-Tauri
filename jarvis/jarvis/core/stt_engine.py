"""Abstract Speech-to-Text Engine"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Optional
from pathlib import Path


@dataclass
class TranscriptionResult:
    """Result of speech transcription"""
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    duration_seconds: Optional[float] = None


class STTEngine(ABC):
    """
    Abstract base class for Speech-to-Text providers.
    
    Implement this interface to add new STT backends like:
    - Whisper (local)
    - Canary (NVIDIA)
    - Cloud providers (Google, Azure, etc.)
    """
    
    @abstractmethod
    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """
        Transcribe audio from a file.
        
        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)
            
        Returns:
            TranscriptionResult with text and metadata
        """
        pass
    
    @abstractmethod
    async def transcribe_bytes(self, audio_bytes: bytes) -> TranscriptionResult:
        """
        Transcribe audio from raw bytes.
        
        Args:
            audio_bytes: Raw audio data
            
        Returns:
            TranscriptionResult with text and metadata
        """
        pass
    
    async def transcribe_stream(
        self, 
        audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[str]:
        """
        Real-time streaming transcription.
        
        Default implementation buffers and transcribes.
        Override for true streaming support.
        
        Args:
            audio_stream: Async iterator of audio chunks
            
        Yields:
            Partial transcription results
        """
        # Default: collect all audio then transcribe
        chunks = []
        async for chunk in audio_stream:
            chunks.append(chunk)
        
        audio_bytes = b"".join(chunks)
        result = await self.transcribe_bytes(audio_bytes)
        yield result.text
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the STT backend is available"""
        pass
