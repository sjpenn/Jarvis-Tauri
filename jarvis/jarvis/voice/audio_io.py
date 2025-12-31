"""Audio I/O - Recording and playback utilities"""

from __future__ import annotations

import asyncio
import wave
import tempfile
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class AudioConfig:
    """Audio recording configuration"""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    format_bits: int = 16


class AudioRecorder:
    """
    Audio recording utility for capturing voice input.
    
    Records until silence is detected or max duration reached.
    """
    
    def __init__(
        self,
        config: Optional[AudioConfig] = None,
        silence_threshold: int = 500,
        silence_duration: float = 1.5,
        max_duration: float = 30.0,
    ):
        self.config = config or AudioConfig()
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.max_duration = max_duration
        self._audio = None
    
    async def record_until_silence(self) -> Path:
        """
        Record audio until silence is detected.
        
        Returns path to temporary WAV file.
        """
        try:
            import pyaudio
        except ImportError:
            raise ImportError("Audio recording requires pyaudio. Install with: pip install pyaudio")
        
        self._audio = pyaudio.PyAudio()
        stream = self._audio.open(
            rate=self.config.sample_rate,
            channels=self.config.channels,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.config.chunk_size,
        )
        
        print("🎙️ Recording... (speak now)")
        
        frames = []
        silent_chunks = 0
        max_chunks = int(self.max_duration * self.config.sample_rate / self.config.chunk_size)
        silence_chunks_threshold = int(self.silence_duration * self.config.sample_rate / self.config.chunk_size)
        
        loop = asyncio.get_event_loop()
        
        for _ in range(max_chunks):
            data = await loop.run_in_executor(
                None,
                lambda: stream.read(self.config.chunk_size, exception_on_overflow=False)
            )
            frames.append(data)
            
            # Check for silence (simple RMS-based)
            rms = self._calculate_rms(data)
            
            if rms < self.silence_threshold:
                silent_chunks += 1
                if silent_chunks >= silence_chunks_threshold:
                    print("🔇 Silence detected, stopping recording")
                    break
            else:
                silent_chunks = 0
        
        stream.stop_stream()
        stream.close()
        self._audio.terminate()
        
        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = Path(temp_file.name)
        temp_file.close()
        
        with wave.open(str(temp_path), 'wb') as wf:
            wf.setnchannels(self.config.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.config.sample_rate)
            wf.writeframes(b''.join(frames))
        
        print(f"📁 Saved recording to {temp_path}")
        return temp_path
    
    def _calculate_rms(self, data: bytes) -> float:
        """Calculate RMS (root mean square) of audio data"""
        import struct
        
        count = len(data) // 2
        shorts = struct.unpack(f"{count}h", data)
        
        sum_squares = sum(s * s for s in shorts)
        rms = (sum_squares / count) ** 0.5
        
        return rms
    
    async def record_duration(self, duration: float) -> Path:
        """
        Record for a fixed duration.
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            Path to temporary WAV file
        """
        try:
            import pyaudio
        except ImportError:
            raise ImportError("Audio recording requires pyaudio. Install with: pip install pyaudio")
        
        self._audio = pyaudio.PyAudio()
        stream = self._audio.open(
            rate=self.config.sample_rate,
            channels=self.config.channels,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.config.chunk_size,
        )
        
        print(f"🎙️ Recording for {duration}s...")
        
        frames = []
        num_chunks = int(duration * self.config.sample_rate / self.config.chunk_size)
        
        loop = asyncio.get_event_loop()
        
        for _ in range(num_chunks):
            data = await loop.run_in_executor(
                None,
                lambda: stream.read(self.config.chunk_size, exception_on_overflow=False)
            )
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        self._audio.terminate()
        
        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = Path(temp_file.name)
        temp_file.close()
        
        with wave.open(str(temp_path), 'wb') as wf:
            wf.setnchannels(self.config.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.config.sample_rate)
            wf.writeframes(b''.join(frames))
        
        return temp_path
