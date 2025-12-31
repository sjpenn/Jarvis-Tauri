"""Voice Loop - Main voice interaction handler"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from jarvis.core.orchestrator import JARVISOrchestrator
from jarvis.voice.wake_word import WakeWordDetector, PorcupineWakeWord, SimpleWakeWord
from jarvis.voice.audio_io import AudioRecorder


class VoiceLoop:
    """
    Main voice interaction loop.
    
    Flow:
    1. Listen for wake word ("JARVIS")
    2. Record user's command
    3. Transcribe (STT)
    4. Process with LLM
    5. Speak response (TTS)
    6. Return to listening for wake word
    """
    
    def __init__(
        self,
        orchestrator: JARVISOrchestrator,
        porcupine_key: Optional[str] = None,
    ):
        self.orchestrator = orchestrator
        self.porcupine_key = porcupine_key
        self.recorder = AudioRecorder()
        self._wake_detector: Optional[WakeWordDetector] = None
        self._running = False
    
    async def start(self) -> None:
        """Start the voice loop"""
        await self.orchestrator.initialize()
        
        # Choose wake word detector
        if self.porcupine_key:
            print("🔑 Using Porcupine wake word detection")
            self._wake_detector = PorcupineWakeWord(
                access_key=self.porcupine_key,
                keyword="jarvis",
            )
        else:
            print("⚠️  No Porcupine key, using Whisper-based wake word (slower)")
            self._wake_detector = SimpleWakeWord()
        
        self._running = True
        
        # Announce startup
        if self.orchestrator.tts:
            await self.orchestrator.tts.speak("JARVIS online and ready, sir.")
        
        # Start listening
        await self._wake_detector.start(self._on_wake)
    
    async def _on_wake(self) -> None:
        """Called when wake word is detected"""
        try:
            # Play acknowledgment sound or speak
            if self.orchestrator.tts:
                await self.orchestrator.tts.speak("Yes?")
            
            # Record user's command
            audio_path = await self.recorder.record_until_silence()
            
            try:
                # Process the voice command
                response = await self.orchestrator.process_voice(audio_path)
                print(f"📝 Response: {response}")
            finally:
                # Clean up temp file
                Path(audio_path).unlink(missing_ok=True)
                
        except Exception as e:
            print(f"❌ Error processing command: {e}")
            if self.orchestrator.tts:
                await self.orchestrator.tts.speak("I'm sorry, I encountered an error.")
    
    async def stop(self) -> None:
        """Stop the voice loop"""
        self._running = False
        
        if self._wake_detector:
            await self._wake_detector.stop()
        
        if self.orchestrator.tts:
            await self.orchestrator.tts.speak("JARVIS shutting down.")


async def run_voice_loop(porcupine_key: Optional[str] = None) -> None:
    """Convenience function to run the voice loop"""
    from jarvis.core.config import load_config
    
    config_path = Path(__file__).parent.parent / "config" / "models.yaml"
    orchestrator = JARVISOrchestrator(config_path=config_path)
    
    loop = VoiceLoop(orchestrator, porcupine_key=porcupine_key)
    
    try:
        await loop.start()
    except KeyboardInterrupt:
        print("\n🛑 Interrupted")
        await loop.stop()
