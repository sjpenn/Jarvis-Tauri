"""macOS TTS Provider - Free local TTS using say command"""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import AsyncIterator, List

from jarvis.core.tts_engine import TTSEngine


class MacOSProvider(TTSEngine):
    """
    macOS native TTS using the 'say' command.
    
    Free, local, no API key required.
    Good quality with Samantha/Daniel voices.
    ~300-500ms latency.
    """
    
    # Available high-quality voices on macOS
    RECOMMENDED_VOICES = [
        "Samantha",  # Female, neutral American
        "Daniel",    # Male, British (closest to JARVIS)
        "Alex",      # Male, American
        "Victoria",  # Female, British
        "Karen",     # Female, Australian
        "Moira",     # Female, Irish
    ]
    
    def __init__(
        self,
        voice: str = "Samantha",
        rate: int = 200,  # Words per minute (default ~175-200)
    ):
        self.voice = voice
        self.rate = rate
    
    async def speak(self, text: str) -> None:
        """Speak text immediately using macOS say"""
        
        # Clean text for speech
        clean_text = self._prepare_text(text)
        
        proc = await asyncio.create_subprocess_exec(
            "/usr/bin/say",
            "-v", self.voice,
            "-r", str(self.rate),
            clean_text,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
    
    async def synthesize(self, text: str) -> bytes:
        """Convert text to audio bytes (AIFF format)"""
        
        clean_text = self._prepare_text(text)
        
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as f:
            temp_path = f.name
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "/usr/bin/say",
                "-v", self.voice,
                "-r", str(self.rate),
                "-o", temp_path,
                clean_text,
            )
            await proc.wait()
            
            with open(temp_path, "rb") as f:
                return f.read()
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    async def save(self, text: str, output_path: Path) -> None:
        """Save speech to an audio file"""
        
        clean_text = self._prepare_text(text)
        output_path = Path(output_path)
        
        # Determine format from extension
        suffix = output_path.suffix.lower()
        
        proc = await asyncio.create_subprocess_exec(
            "/usr/bin/say",
            "-v", self.voice,
            "-r", str(self.rate),
            "-o", str(output_path),
            clean_text,
        )
        await proc.wait()
    
    async def speak_stream(self, text_stream: AsyncIterator[str]) -> None:
        """
        Stream speech as text arrives.
        
        macOS say doesn't support true streaming, so we buffer
        sentences/phrases and speak them as they complete.
        """
        buffer = ""
        sentence_enders = ".!?;"
        
        async for chunk in text_stream:
            buffer += chunk
            
            # Check for complete sentences to speak
            for ender in sentence_enders:
                if ender in buffer:
                    # Split on sentence boundary
                    idx = buffer.rfind(ender)
                    to_speak = buffer[:idx + 1]
                    buffer = buffer[idx + 1:]
                    
                    if to_speak.strip():
                        await self.speak(to_speak.strip())
                    break
        
        # Speak remaining buffer
        if buffer.strip():
            await self.speak(buffer.strip())
    
    def _prepare_text(self, text: str) -> str:
        """Clean and prepare text for speech synthesis"""
        # Remove markdown formatting
        text = text.replace("**", "").replace("*", "")
        text = text.replace("```", "").replace("`", "")
        text = text.replace("#", "")
        
        # Remove URLs (speak as "link")
        import re
        text = re.sub(r'https?://\S+', 'link', text)
        
        # Clean up excessive whitespace
        text = " ".join(text.split())
        
        return text
    
    def get_available_voices(self) -> List[str]:
        """List all available macOS voices"""
        try:
            result = subprocess.run(
                ["/usr/bin/say", "-v", "?"],
                capture_output=True,
                text=True
            )
            voices = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    # Format: "VoiceName   en_US  # Comment"
                    voice_name = line.split()[0]
                    voices.append(voice_name)
            return voices
        except Exception:
            return self.RECOMMENDED_VOICES
    
    async def health_check(self) -> bool:
        """Check if say command is available"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "/usr/bin/say", "--version",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return proc.returncode == 0
        except Exception:
            return False
    
    async def show_notification(self, text: str, title: str = "JARVIS") -> None:
        """Show macOS notification alongside speech"""
        script = f'display notification "{text}" with title "{title}"'
        await asyncio.create_subprocess_exec(
            "/usr/bin/osascript", "-e", script,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
