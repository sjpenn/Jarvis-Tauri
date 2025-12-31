"""TTS Provider implementations"""

from .macos_provider import MacOSProvider

__all__ = ["MacOSProvider"]

# Optional imports for cloud/advanced providers
try:
    from .elevenlabs_provider import ElevenLabsProvider
    __all__.append("ElevenLabsProvider")
except ImportError:
    pass
