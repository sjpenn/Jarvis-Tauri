"""Abstract Vision Engine"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path


class VisionEngine(ABC):
    """Abstract base class for Vision providers"""
    
    @abstractmethod
    async def analyze_image(self, image_path: Path, prompt: str) -> str:
        """
        Analyze a local image file.
        
        Args:
            image_path: Path to the image file
            prompt: Question or prompt about the image
            
        Returns:
            Text description or answer
        """
        pass
    
    @abstractmethod
    async def analyze_screen(self, prompt: str) -> str:
        """
        Capture and analyze the current screen content.
        
        Args:
            prompt: Question about what's on screen
        """
        pass
    
    @abstractmethod
    async def analyze_camera(self, prompt: str) -> str:
        """
        Capture and analyze webcam feed.
        
        Args:
            prompt: Question about what the camera sees
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if vision provider is available"""
        pass
