"""Voice module - Wake word detection and audio I/O"""

from .wake_word import WakeWordDetector
from .audio_io import AudioRecorder

__all__ = ["WakeWordDetector", "AudioRecorder"]
