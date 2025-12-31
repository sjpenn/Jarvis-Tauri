"""Abstract Text-to-Speech Engine"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List
from typing import AsyncIterator, Optional
from pathlib import Path


class TTSEngine(ABC):
    """
    Abstract base class for Text-to-Speech providers.
    
    Implement this interface to add new TTS backends like:
    - macOS say (local, free)
    - ElevenLabs (cloud, premium)
    - Orpheus (local, open-source)
    """
    
    @abstractmethod
    async def speak(self, text: str) -> None:
        """
        Convert text to speech and play immediately.
        
        Args:
            text: Text to speak
        """
        pass
    
    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """
        Convert text to audio bytes without playing.
        
        Args:
            text: Text to synthesize
            
        Returns:
            Raw audio bytes (WAV or MP3)
        """
        pass
    
    @abstractmethod
    async def save(self, text: str, output_path: Path) -> None:
        """
        Convert text to speech and save to file.
        
        Args:
            text: Text to synthesize
            output_path: Where to save the audio file
        """
        pass
    
    async def speak_stream(self, text_stream: AsyncIterator[str]) -> None:
        """
        Stream audio output as text arrives.
        
        Enables sub-200ms latency by starting speech
        before the full response is generated.
        
        Default implementation buffers then speaks.
        Override for true streaming support.
        
        Args:
            text_stream: Async iterator of text chunks
        """
        # Default: collect all text then speak
        chunks = []
        async for chunk in text_stream:
            chunks.append(chunk)
        
        full_text = "".join(chunks)
        await self.speak(full_text)
    
    @abstractmethod
    def get_available_voices(self) -> List[str]:
        """List available voices for this provider"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the TTS backend is available"""
        pass
