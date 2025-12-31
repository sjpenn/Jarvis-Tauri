"""Wake Word Detection - Listens for 'JARVIS' to activate"""

from __future__ import annotations

import asyncio
import struct
import wave
import tempfile
from pathlib import Path
from typing import Optional, Callable, Awaitable
from abc import ABC, abstractmethod


class WakeWordDetector(ABC):
    """Abstract wake word detector interface"""
    
    @abstractmethod
    async def start(self, on_wake: Callable[[], Awaitable[None]]) -> None:
        """Start listening for wake word, call on_wake when detected"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop listening"""
        pass


class PorcupineWakeWord(WakeWordDetector):
    """
    Wake word detection using Picovoice Porcupine.
    
    Uses the built-in "jarvis" wake word.
    Requires PORCUPINE_ACCESS_KEY environment variable.
    
    Get a free key at: https://console.picovoice.ai/
    """
    
    def __init__(
        self,
        access_key: str,
        keyword: str = "jarvis",
        sensitivity: float = 0.5,
    ):
        self.access_key = access_key
        self.keyword = keyword
        self.sensitivity = sensitivity
        self._porcupine = None
        self._audio = None
        self._stream = None
        self._running = False
    
    async def start(self, on_wake: Callable[[], Awaitable[None]]) -> None:
        """Start listening for 'JARVIS' wake word"""
        try:
            import pvporcupine
            import pyaudio
        except ImportError:
            raise ImportError(
                "Wake word requires pvporcupine and pyaudio. "
                "Install with: pip install pvporcupine pyaudio"
            )
        
        # Initialize Porcupine with built-in "jarvis" keyword
        self._porcupine = pvporcupine.create(
            access_key=self.access_key,
            keywords=[self.keyword],
            sensitivities=[self.sensitivity],
        )
        
        # Initialize PyAudio
        self._audio = pyaudio.PyAudio()
        self._stream = self._audio.open(
            rate=self._porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self._porcupine.frame_length,
        )
        
        self._running = True
        print(f"🎤 Listening for '{self.keyword.upper()}'...")
        
        # Run detection loop in thread pool
        loop = asyncio.get_event_loop()
        while self._running:
            # Read audio frame
            pcm = await loop.run_in_executor(
                None,
                lambda: self._stream.read(self._porcupine.frame_length, exception_on_overflow=False)
            )
            pcm = struct.unpack_from("h" * self._porcupine.frame_length, pcm)
            
            # Check for wake word
            keyword_index = self._porcupine.process(pcm)
            
            if keyword_index >= 0:
                print(f"✨ Wake word '{self.keyword.upper()}' detected!")
                await on_wake()
    
    async def stop(self) -> None:
        """Stop listening"""
        self._running = False
        
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        
        if self._audio:
            self._audio.terminate()
            self._audio = None
        
        if self._porcupine:
            self._porcupine.delete()
            self._porcupine = None


class SimpleWakeWord(WakeWordDetector):
    """
    Simple wake word detection using Whisper.
    
    Falls back to transcribing short audio clips and checking
    for "jarvis" in the text. Less efficient but works without
    Porcupine API key.
    """
    
    def __init__(self, whisper_model: str = "tiny.en"):
        self.whisper_model = whisper_model
        self._running = False
        self._stt = None
    
    async def start(self, on_wake: Callable[[], Awaitable[None]]) -> None:
        """Start listening using Whisper-based detection"""
        try:
            import pyaudio
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError(
                "Wake word requires pyaudio and faster-whisper. "
                "Install with: pip install pyaudio faster-whisper"
            )
        
        # Use tiny model for fast wake word detection
        self._stt = WhisperModel(self.whisper_model, device="auto", compute_type="auto")
        
        audio = pyaudio.PyAudio()
        stream = audio.open(
            rate=16000,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=1024,
        )
        
        self._running = True
        print("🎤 Listening for 'JARVIS'... (Whisper-based detection)")
        
        loop = asyncio.get_event_loop()
        
        while self._running:
            # Record 2 seconds of audio
            frames = []
            for _ in range(0, int(16000 / 1024 * 2)):
                if not self._running:
                    break
                data = await loop.run_in_executor(
                    None,
                    lambda: stream.read(1024, exception_on_overflow=False)
                )
                frames.append(data)
            
            if not self._running:
                break
            
            # Save to temp file and transcribe
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
                wf = wave.open(temp_path, 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b''.join(frames))
                wf.close()
            
            try:
                # Transcribe
                segments, _ = self._stt.transcribe(
                    temp_path,
                    language="en",
                    vad_filter=True,
                )
                text = " ".join([s.text for s in segments]).lower()
                
                # Check for wake word
                if "jarvis" in text:
                    print(f"✨ Detected: '{text}'")
                    await on_wake()
            finally:
                Path(temp_path).unlink(missing_ok=True)
        
        stream.stop_stream()
        stream.close()
        audio.terminate()
    
    async def stop(self) -> None:
        """Stop listening"""
        self._running = False
