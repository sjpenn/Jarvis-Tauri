"""Ollama Vision Provider - Implementation using Llava/Moondream"""

from __future__ import annotations

import asyncio
import base64
import tempfile
from pathlib import Path
from typing import Optional
import mss
import cv2
import ollama
from PIL import Image

from jarvis.core.vision_engine import VisionEngine


class OllamaVisionProvider(VisionEngine):
    """
    Vision provider using local Ollama models (Llava, Moondream, etc.)
    """
    
    def __init__(self, model_name: str = "llava:7b"):
        self.model = model_name
        self._camera_index = 0
    
    async def analyze_image(self, image_path: Path, prompt: str) -> str:
        """Analyze local image using Ollama"""
        try:
            # Run in executor to avoid blocking main thread
            response = await asyncio.to_thread(
                self._generate, image_path, prompt
            )
            return response
        except Exception as e:
            return f"Error analyzing image: {e}"
    
    async def analyze_screen(self, prompt: str) -> str:
        """Capture screenshot and analyze"""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            # Capture screen using mss
            with mss.mss() as sct:
                # Capture primary monitor
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                
                # Convert to PIL Image and save
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                # Resize if too large (for speed)
                max_size = (1024, 1024)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                img.save(temp_path)
            
            # Analyze
            return await self.analyze_image(temp_path, prompt)
            
        finally:
            temp_path.unlink(missing_ok=True)

    async def analyze_camera(self, prompt: str) -> str:
        """Capture webcam frame and analyze"""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            temp_path = Path(f.name)
            
        try:
            cam = cv2.VideoCapture(self._camera_index)
            if not cam.isOpened():
                return "Error: Could not access camera."
            
            # Read frame
            ret, frame = cam.read()
            cam.release()
            
            if not ret:
                return "Error: Failed to capture frame."
            
            # Save frame
            cv2.imwrite(str(temp_path), frame)
            
            # Analyze
            return await self.analyze_image(temp_path, prompt)
            
        finally:
            temp_path.unlink(missing_ok=True)
    
    def _generate(self, image_path: Path, prompt: str) -> str:
        """Internal synchronous call to Ollama"""
        res = ollama.generate(
            model=self.model,
            prompt=prompt,
            images=[image_path]
        )
        return res['response']
    
    async def health_check(self) -> bool:
        """Check if model is available"""
        try:
            # Just check if we can list models
            models = await asyncio.to_thread(ollama.list)
            # Check if our model is pulled, if not try to pull it (or fail)
            return any(m['name'].startswith(self.model) for m in models['models'])
        except Exception:
            return False
