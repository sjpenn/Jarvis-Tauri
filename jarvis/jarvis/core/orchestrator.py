"""JARVIS Orchestrator - Main coordination and event loop"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional

from jarvis.core.config import Settings, load_config
from jarvis.core.llm_engine import LLMEngine, LLMResponse, Tool, ToolCall
from jarvis.core.stt_engine import STTEngine
from jarvis.core.tts_engine import TTSEngine
from jarvis.core.vision_engine import VisionEngine
from jarvis.integrations.base import Integration
from jarvis.agents.connectors.connector_base import ConnectorConfig


class JARVISOrchestrator:
    """
    Main JARVIS orchestrator that coordinates all components.
    
    Responsibilities:
    - Initialize and manage LLM, STT, TTS engines
    - Register and route integration tools
    - Process voice and text inputs
    - Execute tool calls from LLM
    - Handle the conversation loop
    """
    
    def __init__(
        self,
        config_path: Optional[Path] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or load_config(config_path)
        self.llm: Optional[LLMEngine] = None
        self.stt: Optional[STTEngine] = None
        self.tts: Optional[TTSEngine] = None
        self.vision: Optional[VisionEngine] = None
        self.integrations: Dict[str, Integration] = {}
        self.conversation_history: List[Dict] = []
        self.memory_integration = None  # Will be MemoryIntegration or None
        self.agent_coordinator = None  # Will be AgentCoordinator or None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize all components based on configuration"""
        if self._initialized:
            return
        
        # Initialize LLM
        self.llm = await self._init_llm()
        
        # Initialize TTS
        self.tts = await self._init_tts()
        
        # Initialize STT (optional, only needed for voice)
        if self.settings.wake_word.enabled:
            self.stt = await self._init_stt()
            
        # Initialize Vision
        if self.settings.vision.provider == "ollama":
            from jarvis.providers.vision import OllamaVisionProvider
            self.vision = OllamaVisionProvider(model_name=self.settings.vision.model)
        
        # Initialize memory (before other integrations)
        if self.settings.memory.enabled:
            from jarvis.integrations.memory_module import MemoryIntegration
            self.memory_integration = MemoryIntegration(
                db_path=self.settings.memory.db_path
            )
            await self.memory_integration.setup()
            self.integrations["memory"] = self.memory_integration
        
        # Initialize integrations
        await self._init_integrations()
        
        self._initialized = True
    
    async def _init_llm(self) -> LLMEngine:
        """Initialize LLM engine based on config"""
        from jarvis.providers.llm import OllamaProvider
        
        return OllamaProvider(
            fast_model=self.settings.llm.fast_model,
            primary_model=self.settings.llm.primary_model,
            fallback_model=self.settings.llm.fallback_model,
            host=self.settings.ollama_host,
            temperature=self.settings.llm.temperature,
            max_tokens=self.settings.llm.max_tokens,
        )
    
    async def _init_tts(self) -> TTSEngine:
        """Initialize TTS engine based on config"""
        if self.settings.tts.provider == "macos":
            from jarvis.providers.tts import MacOSProvider
            return MacOSProvider(
                voice=self.settings.tts.voice,
            )
        elif self.settings.tts.provider == "elevenlabs":
            from jarvis.providers.tts.elevenlabs_provider import ElevenLabsProvider
            if not self.settings.elevenlabs_api_key:
                raise ValueError("ElevenLabs API key required for elevenlabs TTS")
            return ElevenLabsProvider(
                api_key=self.settings.elevenlabs_api_key,
                voice=self.settings.tts.voice,
            )
        else:
            # Default to macOS
            from jarvis.providers.tts import MacOSProvider
            return MacOSProvider()
    
    async def _init_stt(self) -> STTEngine:
        """Initialize STT engine based on config"""
        from jarvis.providers.stt import WhisperProvider
        
        return WhisperProvider(
            model_size=self.settings.stt.model,
            language=self.settings.stt.language,
            device=self.settings.stt.device,
        )
    
    async def _init_integrations(self) -> None:
        """Initialize enabled integrations"""
        if self.settings.integrations.calendar_enabled:
            from jarvis.integrations import CalendarIntegration
            cal = CalendarIntegration()
            await cal.setup()
            self.integrations["calendar"] = cal
        
        if self.settings.integrations.tasks_enabled:
            from jarvis.integrations import TasksIntegration
            tasks = TasksIntegration()
            await tasks.setup()
            self.integrations["tasks"] = tasks
        
        # Initialize Agent Coordinator (agentic orchestration layer)
        await self._init_agent_coordinator()
    
    async def _init_agent_coordinator(self) -> None:
        """
        Initialize the agentic orchestration layer.
        
        Sets up domain agents (email, calendar, transport) with their
        connectors based on configuration. All actions go through
        draft mode for user approval.
        """
        from jarvis.agents.coordinator import AgentCoordinator
        from jarvis.agents.email_agent import EmailAgent
        from jarvis.agents.calendar_agent import CalendarAgent
        from jarvis.agents.transport_agent import TransportAgent
        
        # Get memory store if available
        memory_store = None
        if self.memory_integration:
            memory_store = self.memory_integration.memory
        
        # Create coordinator
        self.agent_coordinator = AgentCoordinator(memory_store)
        
        # Initialize Email Agent if configured
        if self.settings.integrations.email_enabled:
            email_agent = EmailAgent()
            
            # Add Gmail connectors
            # Add Gmail connectors
            gmail_accounts = []
            if getattr(self.settings, 'agents', None) and getattr(self.settings.agents, 'email', None):
                 gmail_accounts = self.settings.agents.email.gmail_accounts
            
            if gmail_accounts:
                from jarvis.agents.connectors.gmail_connector import GmailConnector

                
                for acct in gmail_accounts:
                    config = ConnectorConfig(
                        name=acct.name,
                        connector_type='gmail',
                        credentials_path=acct.credentials_file,
                    )
                    email_agent.register_connector(GmailConnector(config))
            
            # Add Outlook connectors
            outlook_accounts = getattr(self.settings, 'outlook_accounts', [])
            if outlook_accounts:
                from jarvis.agents.connectors.outlook_connector import OutlookConnector

                
                for acct in outlook_accounts:
                    config = ConnectorConfig(
                        name=acct.get('name', 'default'),
                        connector_type='outlook',
                        extra={'client_id': acct.get('client_id')},
                    )
                    email_agent.register_connector(OutlookConnector(config))
            
            self.agent_coordinator.register_agent(email_agent)
        
        # Initialize Calendar Agent (enhanced version)
        calendar_agent = CalendarAgent()
        self.agent_coordinator.register_agent(calendar_agent)
        
        # Initialize Transport Agent if configured
        transport_config = getattr(self.settings, 'transport', None)
        agents_config = getattr(self.settings, 'agents', None)
        
        # Get transport config from either location
        if agents_config:
            transport_config = getattr(agents_config, 'transport', transport_config)
        
        if transport_config and getattr(transport_config, 'enabled', False):
            transport_agent = TransportAgent()
            
            # Get locations and providers from config
            locations = None
            providers = None
            
            if hasattr(transport_config, 'locations'):
                locations = transport_config.locations
                if hasattr(locations, '__dict__'):
                    locations = {k: v.__dict__ if hasattr(v, '__dict__') else v 
                                for k, v in locations.__dict__.items()}
            
            if hasattr(transport_config, 'providers'):
                providers = transport_config.providers
                if providers:
                    # Convert to list of dicts if needed
                    providers = [p.__dict__ if hasattr(p, '__dict__') else p for p in providers]
            
            # Configure agent
            transport_agent.configure(
                home_station=getattr(transport_config, 'home_station', None),
                default_destination=getattr(transport_config, 'default_destination', None),
                current_location=getattr(transport_config, 'location', None),
                locations=locations,
                providers=providers,
            )
            
            # Add transport connectors based on config
            if providers:
                for prov in providers:

                    prov_name = prov.get('name', '') if isinstance(prov, dict) else getattr(prov, 'name', '')
                    prov_enabled = prov.get('enabled', False) if isinstance(prov, dict) else getattr(prov, 'enabled', False)
                    
                    if prov_name == 'wmata' and prov_enabled:
                        from jarvis.agents.connectors.wmata_connector import WMATAConnector
                        
                        api_key = prov.get('api_key', '') if isinstance(prov, dict) else getattr(prov, 'api_key', '')
                        config = ConnectorConfig(
                            name='wmata',
                            connector_type='wmata',
                            api_key=api_key,
                        )
                        transport_agent.register_connector(WMATAConnector(config))
                    
                    elif prov_name == 'capital_bikeshare' and prov_enabled:
                        from jarvis.agents.connectors.bikeshare_connector import CapitalBikeshareConnector
                        
                        config = ConnectorConfig(
                            name='capital_bikeshare',
                            connector_type='bikeshare',
                        )
                        transport_agent.register_connector(CapitalBikeshareConnector(config))
                    
                    elif prov_name == 'amtrak' and prov_enabled:
                        from jarvis.agents.connectors.amtrak_connector import AmtrakConnector
                        
                        # No API key needed - uses free Amtraker API
                        config = ConnectorConfig(
                            name='amtrak',
                            connector_type='amtrak',
                        )
                        transport_agent.register_connector(AmtrakConnector(config))
                    
                    elif prov_name == 'vre' and prov_enabled:
                        from jarvis.agents.connectors.vre_connector import VREConnector
                        
                        # No API key needed - uses free VRE GTFS-RT feed
                        config = ConnectorConfig(
                            name='vre',
                            connector_type='vre',
                        )
                        transport_agent.register_connector(VREConnector(config))
                    
                    elif prov_name == 'marc' and prov_enabled:
                        from jarvis.agents.connectors.marc_connector import MARCConnector
                        
                        # No API key needed - uses free MTA GTFS-RT feed
                        config = ConnectorConfig(
                            name='marc',
                            connector_type='marc',
                        )
                        config = ConnectorConfig(
                            name='marc',
                            connector_type='marc',
                        )
                        transport_agent.register_connector(MARCConnector(config))

                    elif prov_name == 'apple_maps' and prov_enabled:
                         from jarvis.agents.connectors.maps_connector import MapsConnector
                         
                         config = ConnectorConfig(
                             name='apple_maps',
                             connector_type='maps',
                         )
                         transport_agent.register_connector(MapsConnector(config))
            
            self.agent_coordinator.register_agent(transport_agent)
        
        # Initialize Weather Agent if configured
        # Uses FREE NOAA weather.gov API - no API key required!
        weather_config = getattr(agents_config, 'weather', None) if agents_config else None
        if weather_config and getattr(weather_config, 'enabled', False):
            from jarvis.agents.weather_agent import WeatherAgent
            from jarvis.agents.connectors.weather_connector import WeatherConnector
            
            weather_agent = WeatherAgent()
            weather_agent.configure(
                default_location=getattr(weather_config, 'default_location', 'Washington, DC'),
            )
            
            units = getattr(weather_config, 'units', 'imperial')
            
            config = ConnectorConfig(
                name='weather.gov',
                connector_type='weather',
                extra={'units': units},
            )
            weather_agent.register_connector(WeatherConnector(config))
            self.agent_coordinator.register_agent(weather_agent)
        
        # Initialize Flight Agent if configured
        flight_config = getattr(agents_config, 'flight', None) if agents_config else None
        if flight_config and getattr(flight_config, 'enabled', False):
            from jarvis.agents.flight_agent import FlightAgent
            from jarvis.agents.connectors.flight_connector import FlightConnector
            
            flight_agent = FlightAgent()
            
            api_key = getattr(flight_config, 'api_key', '')
            config = ConnectorConfig(
                name='aviationstack',
                connector_type='flight',
                api_key=api_key,
            )
            flight_agent.register_connector(FlightConnector(config))
            self.agent_coordinator.register_agent(flight_agent)
        
        # Initialize Trip Planning Agent if configured
        trip_config = getattr(agents_config, 'trip', None) if agents_config else None
        if trip_config and getattr(trip_config, 'enabled', False):
            from jarvis.agents.trip_agent import TripPlanAgent
            from jarvis.agents.connectors.hotel_connector import HotelConnector
            
            trip_agent = TripPlanAgent()
            
            api_key = getattr(trip_config, 'api_key', '')
            config = ConnectorConfig(
                name='hotel',
                connector_type='hotel',
                api_key=api_key,
            )
            trip_agent.register_connector(HotelConnector(config))
            self.agent_coordinator.register_agent(trip_agent)
        
        # Setup all agents
        await self.agent_coordinator.setup()
    
    def _get_system_prompt(self) -> str:
        """
        Build the system prompt with memory context.
        
        Includes user profile, preferences, and important memories
        so JARVIS knows who it's talking to.
        """
        base_prompt = """You are JARVIS, an advanced AI assistant inspired by Tony Stark's AI.

**Personality:**
- Helpful, witty, and slightly formal
- Proactive in offering relevant information
- Concise but thorough

**Capabilities:**
- Real-time access to calendar, email, documents, and tasks
- Voice interaction through speech recognition and synthesis
- Autonomous execution of approved actions
- Persistent memory to remember user information and preferences

**Memory Usage:**
- When the user tells you their name, use the set_user_name tool
- When the user shares preferences, use set_preference to remember them
- Use remember_about_user for important facts about the user
- Check recall_user_info when you need to personalize responses

**Behavior:**
- Anticipate needs before asked
- Provide concise, actionable responses
- Explain reasoning for complex decisions
- Use tools when appropriate to complete tasks
- Address the user by name when known

Always respond naturally as if speaking out loud. Keep responses concise for voice output."""
        
        # Add memory context if available
        if self.memory_integration:
            memory_context = self.memory_integration.get_context_for_prompt()
            if memory_context:
                base_prompt += f"\n\n**Known User Context:**\n{memory_context}"
        
        return base_prompt
    
    def get_all_tools(self) -> List[Tool]:
        """Collect tools from all integrations and agent coordinator"""
        tools = []
        for integration in self.integrations.values():
            tools.extend(integration.tools)
        
        # Add agent coordinator tools
        if self.agent_coordinator:
            tools.extend(self.agent_coordinator.get_tools())
        
        return tools
    
    async def execute_tool(self, tool_call: ToolCall) -> str:
        """Route and execute a tool call"""
        # Check integrations first
        for integration in self.integrations.values():
            for tool in integration.tools:
                if tool.name == tool_call.name:
                    result = await integration.execute(
                        tool_call.name,
                        tool_call.arguments
                    )
                    return str(result)
        
        # Check agent coordinator tools
        if self.agent_coordinator:
            for tool in self.agent_coordinator.get_tools():
                if tool.name == tool_call.name:
                    result = await self.agent_coordinator.execute_tool(
                        tool_call.name,
                        tool_call.arguments
                    )
                    return str(result)
        
        return f"Unknown tool: {tool_call.name}"
    
    async def chat(self, message: str, speak: bool = True) -> str:
        """
        Process a text message and optionally speak the response.
        
        Args:
            message: User's text message
            speak: Whether to speak the response via TTS
            
        Returns:
            JARVIS's text response
        """
        await self.initialize()
        
        # Get available tools
        tools = self.get_all_tools()
        
        # Get system prompt with memory context
        system_prompt = self._get_system_prompt()
        
        # Query LLM
        response = await self.llm.reason(
            prompt=message,
            tools=tools if tools else None,
            system_prompt=system_prompt,
            conversation_history=self.conversation_history,
        )
        
        # Handle tool calls
        if response.tool_calls:
            tool_results = []
            for tool_call in response.tool_calls:
                result = await self.execute_tool(tool_call)
                tool_results.append(f"{tool_call.name}: {result}")
            
            # Feed tool results back to LLM for final response
            tool_context = "\n".join(tool_results)
            follow_up = await self.llm.reason(
                prompt=f"Tool results:\n{tool_context}\n\nProvide a natural response to the user based on these results.",
                conversation_history=self.conversation_history,
            )
            final_response = follow_up.content
        else:
            final_response = response.content
        
        # Update conversation history
        self.conversation_history.append({"role": "user", "content": message})
        self.conversation_history.append({"role": "assistant", "content": final_response})
        
        # Keep history manageable (last 20 exchanges)
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]
        
        # Speak response
        if speak and self.tts:
            await self.tts.speak(final_response)
        
        return final_response
    
    async def stream_chat(self, message: str, speak: bool = False) -> AsyncIterator[str]:
        """
        Stream a response token-by-token for real-time UI updates.
        
        Args:
            message: User's text message
            speak: Whether to queue TTS after completion
            
        Yields:
            Response tokens as they are generated
        """
        await self.initialize()
        
        # Get system prompt with memory context
        system_prompt = self._get_system_prompt()
        
        # Track the full response for history
        full_response = []
        
        # Stream from LLM with system prompt and history
        async for token in self.llm.stream(
            prompt=message,
            system_prompt=system_prompt,
            conversation_history=self.conversation_history,
        ):
            full_response.append(token)
            yield token
        
        # Build final response
        final_response = "".join(full_response)
        
        # Update conversation history
        self.conversation_history.append({"role": "user", "content": message})
        self.conversation_history.append({"role": "assistant", "content": final_response})
        
        # Keep history manageable (last 20 exchanges)
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]
        
        # Speak response after streaming completes
        if speak and self.tts:
            await self.tts.speak(final_response)


    
    async def process_voice(self, audio_path: Path) -> str:
        """
        Process voice input: STT → LLM → TTS
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            JARVIS's response text
        """
        await self.initialize()
        
        if not self.stt:
            return "Speech recognition not enabled"
        
        # Transcribe audio
        result = await self.stt.transcribe(audio_path)
        
        if not result.text.strip():
            return "I didn't catch that. Could you repeat?"
        
        # Process the transcribed text
        return await self.chat(result.text, speak=True)

    async def process_image(self, image_path: Path, prompt: str = "What do you see?") -> str:
        """
        Process an image using Vision engine first, then LLM.
        
        Args:
            image_path: Path to image
            Returns:
            Analysis text
        """
        await self.initialize()
        
        if not self.vision:
            return "Vision capabilities not enabled."
            
        # Analyze with Vision model
        vision_response = await self.vision.analyze_image(image_path, prompt)
        
        # Optional: Feed result to LLM for more conversational tone?
        # For now, just return the vision model's response directly
        return vision_response


    async def process_screen(self, prompt: str = "What is on the screen?") -> str:
        """Capture and analyze screen"""
        await self.initialize()
        if not self.vision:
            return "Vision capabilities not enabled."
        return await self.vision.analyze_screen(prompt)

    async def process_camera(self, prompt: str = "What do you see?") -> str:
        """Capture and analyze webcam"""
        await self.initialize()
        if not self.vision:
            return "Vision capabilities not enabled."
        return await self.vision.analyze_camera(prompt)
    
    async def health_check(self) -> dict:
        """Check health of all components"""
        await self.initialize()
        
        status = {
            "llm": await self.llm.health_check() if self.llm else False,
            "tts": await self.tts.health_check() if self.tts else False,
            "stt": await self.stt.health_check() if self.stt else False,
            "integrations": {},
        }
        
        for name, integration in self.integrations.items():
            status["integrations"][name] = await integration.health_check()
        
        return status
    
    def clear_history(self) -> None:
        """Clear conversation history"""
        self.conversation_history = []
