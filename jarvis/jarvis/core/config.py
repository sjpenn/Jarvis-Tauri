"""Configuration system for JARVIS using Pydantic Settings"""

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml


class LLMConfig(BaseModel):
    """LLM provider configuration"""
    provider: Literal["ollama", "openai"] = "ollama"
    fast_model: str = "qwen2.5:3b"  # Fast responses
    primary_model: str = "qwen2.5:14b-instruct-q5_K_M"
    fallback_model: str = "phi4:latest"
    temperature: float = 0.7
    max_tokens: int = 2048


class STTConfig(BaseModel):
    """Speech-to-Text configuration"""
    provider: Literal["whisper", "canary"] = "whisper"
    model: str = "large-v3-turbo"
    language: str = "en"
    device: str = "auto"


class TTSConfig(BaseModel):
    """Text-to-Speech configuration"""
    provider: Literal["macos", "elevenlabs", "orpheus"] = "macos"
    voice: str = "Samantha"
    speed: float = 1.0


class WakeWordConfig(BaseModel):
    """Wake word detection configuration"""
    enabled: bool = True
    keyword: str = "jarvis"
    sensitivity: float = 0.5


class VisionConfig(BaseModel):
    """Vision configuration"""
    provider: Literal["ollama"] = "ollama"
    model: str = "llava:7b"
    camera_index: int = 0


class IntegrationsConfig(BaseModel):
    """Integration toggles"""
    calendar_enabled: bool = True
    email_enabled: bool = True
    documents_enabled: bool = False
    web_search_enabled: bool = False
    tasks_enabled: bool = True
    memory_enabled: bool = True


class MemoryConfig(BaseModel):
    """Memory system configuration"""
    enabled: bool = True
    db_path: str = "~/.jarvis/memory.db"
    auto_extract_preferences: bool = True




class GmailAccount(BaseModel):
    name: str
    credentials_file: str

class OutlookAccount(BaseModel):
    name: str
    client_id: str

class EmailAgentConfig(BaseModel):
    enabled: bool = True
    gmail_accounts: List[GmailAccount] = Field(default_factory=list)
    outlook_accounts: List[OutlookAccount] = Field(default_factory=list)

class TransportAgentConfig(BaseModel):
    enabled: bool = True
    locations: Dict[str, Any] = Field(default_factory=dict)
    providers: List[Any] = Field(default_factory=list)

class WeatherAgentConfig(BaseModel):
    enabled: bool = True
    provider: str = "weather.gov"
    default_location: str = "Washington, DC"
    units: str = "imperial"

class FlightAgentConfig(BaseModel):
    enabled: bool = True
    provider: str = "aviationstack"
    api_key: str = ""

class TripAgentConfig(BaseModel):
    enabled: bool = True
    hotel_provider: str = "demo"
    api_key: str = ""

class AgentsConfig(BaseModel):
    email: EmailAgentConfig = Field(default_factory=EmailAgentConfig)
    transport: TransportAgentConfig = Field(default_factory=TransportAgentConfig)
    weather: WeatherAgentConfig = Field(default_factory=WeatherAgentConfig)
    flight: FlightAgentConfig = Field(default_factory=FlightAgentConfig)
    trip: TripAgentConfig = Field(default_factory=TripAgentConfig)
    calendar: Dict[str, Any] = Field(default_factory=dict)


class Settings(BaseSettings):
    """Main JARVIS settings loaded from environment and config files"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # API Keys from environment
    ollama_host: str = "http://127.0.0.1:11434"
    elevenlabs_api_key: Optional[str] = None
    porcupine_access_key: Optional[str] = None
    perplexity_api_key: Optional[str] = None
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    
    # Component configs (loaded from YAML)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    stt: STTConfig = Field(default_factory=STTConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    wake_word: WakeWordConfig = Field(default_factory=WakeWordConfig)
    vision: VisionConfig = Field(default_factory=VisionConfig)
    integrations: IntegrationsConfig = Field(default_factory=IntegrationsConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)


def load_config(config_path: Optional[Path] = None) -> Settings:
    """Load settings from YAML config file and environment"""
    
    settings = Settings()
    
    if config_path and config_path.exists():
        with open(config_path) as f:
            yaml_config = yaml.safe_load(f)
        
        if yaml_config:
            if "llm" in yaml_config:
                settings.llm = LLMConfig(**yaml_config["llm"])
            if "stt" in yaml_config:
                settings.stt = STTConfig(**yaml_config["stt"])
            if "tts" in yaml_config:
                settings.tts = TTSConfig(**yaml_config["tts"])
            if "wake_word" in yaml_config:
                settings.wake_word = WakeWordConfig(**yaml_config["wake_word"])
            if "vision" in yaml_config:
                settings.vision = VisionConfig(**yaml_config["vision"])
            if "integrations" in yaml_config:
                settings.integrations = IntegrationsConfig(**yaml_config["integrations"])
            if "memory" in yaml_config:
                settings.memory = MemoryConfig(**yaml_config["memory"])
            if "agents" in yaml_config:
                settings.agents = AgentsConfig(**yaml_config["agents"])
    
    return settings
