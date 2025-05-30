"""
WebSocket Client for Simple Agent

Handles communication with the Simple Agent WebSocket server.
"""

import asyncio
import logging
import socketio
from typing import Callable, Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    """Agent execution status."""
    IDLE = "idle"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    ERROR = "error"

class SimpleAgentWebSocketClient:
    """WebSocket client for Simple Agent server communication."""
    
    def __init__(self, server_url: str, timeout: int = 300):
        """
        Initialize the WebSocket client.
        
        Args:
            server_url: URL of the Simple Agent WebSocket server
            timeout: Connection timeout in seconds
        """
        self.server_url = server_url
        self.timeout = timeout
        self.sio = socketio.AsyncClient(
            logger=False,
            engineio_logger=False
        )
        self.connected = False
        self.status = AgentStatus.IDLE
        
        # Event handlers based on actual Simple Agent WebSocket API
        self.on_agent_started: Optional[Callable] = None
        self.on_step_start: Optional[Callable] = None
        self.on_assistant_message: Optional[Callable] = None
        self.on_tool_call: Optional[Callable] = None
        self.on_step_summary: Optional[Callable] = None
        self.on_final_summary: Optional[Callable] = None
        self.on_tool_result: Optional[Callable] = None
        self.on_file_created: Optional[Callable] = None
        self.on_directory_changed: Optional[Callable] = None
        self.on_task_completed: Optional[Callable] = None
        self.on_agent_finished: Optional[Callable] = None
        self.on_agent_error: Optional[Callable] = None
        self.on_waiting_for_input: Optional[Callable] = None
        
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Set up WebSocket event handlers based on Simple Agent WebSocket API."""
        
        @self.sio.event
        async def connect():
            """Handle connection established."""
            logger.info("Connected to Simple Agent WebSocket server")
            self.connected = True
        
        @self.sio.event
        async def disconnect():
            """Handle disconnection."""
            logger.info("Disconnected from Simple Agent WebSocket server")
            self.connected = False
            self.status = AgentStatus.IDLE
        
        @self.sio.event
        async def connect_error(data):
            """Handle connection error."""
            logger.error(f"WebSocket connection error: {data}")
            self.connected = False
        
        @self.sio.event
        async def agent_started(data):
            """Handle agent started event."""
            logger.info("Agent execution started")
            self.status = AgentStatus.RUNNING
            if self.on_agent_started:
                await self.on_agent_started(data)
        
        @self.sio.event
        async def step_start(data):
            """Handle step start event."""
            logger.debug(f"Step started: {data}")
            if self.on_step_start:
                await self.on_step_start(data)
        
        @self.sio.event
        async def assistant_message(data):
            """Handle assistant message event."""
            logger.debug(f"Assistant message: {data}")
            if self.on_assistant_message:
                await self.on_assistant_message(data)
        
        @self.sio.event
        async def tool_call(data):
            """Handle tool call event."""
            logger.debug(f"Tool call: {data}")
            if self.on_tool_call:
                await self.on_tool_call(data)
        
        @self.sio.event
        async def tool_result(data):
            """Handle tool result event."""
            logger.debug(f"Tool result: {data}")
            if self.on_tool_result:
                await self.on_tool_result(data)
        
        @self.sio.event
        async def step_summary(data):
            """Handle step summary event."""
            logger.debug(f"Step summary: {data}")
            if self.on_step_summary:
                await self.on_step_summary(data)
        
        @self.sio.event
        async def final_summary(data):
            """Handle final summary event."""
            logger.info(f"Final summary: {data}")
            if self.on_final_summary:
                await self.on_final_summary(data)
        
        @self.sio.event
        async def file_created(data):
            """Handle file created event."""
            logger.info(f"File created event received: {data}")
            if self.on_file_created:
                await self.on_file_created(data)
        
        @self.sio.event
        async def directory_changed(data):
            """Handle directory changed event."""
            logger.debug(f"Directory changed: {data}")
            if self.on_directory_changed:
                await self.on_directory_changed(data)
        
        @self.sio.event
        async def task_completed(data):
            """Handle task completed event."""
            logger.info("Task completed successfully")
            self.status = AgentStatus.COMPLETED
            if self.on_task_completed:
                await self.on_task_completed(data)
        
        @self.sio.event
        async def agent_finished(data):
            """Handle agent finished event."""
            logger.info("Agent execution finished")
            self.status = AgentStatus.IDLE
            if self.on_agent_finished:
                await self.on_agent_finished(data)
        
        @self.sio.event
        async def agent_error(data):
            """Handle agent error event."""
            logger.error(f"Agent error: {data}")
            self.status = AgentStatus.ERROR
            if self.on_agent_error:
                await self.on_agent_error(data)
        
        # Handle waiting for input (this might be sent as assistant_message with special content)
        @self.sio.event
        async def waiting_for_input(data):
            """Handle waiting for input event."""
            logger.info("Agent waiting for user input")
            self.status = AgentStatus.WAITING_INPUT
            if self.on_waiting_for_input:
                await self.on_waiting_for_input(data)
    
    async def connect(self) -> bool:
        """
        Connect to the WebSocket server.
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            await self.sio.connect(
                self.server_url,
                wait_timeout=self.timeout
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket server: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the WebSocket server."""
        if self.connected:
            await self.sio.disconnect()
    
    async def run_agent(
        self,
        instruction: str,
        max_steps: int = 20,
        auto_continue: int = 0
    ) -> bool:
        """
        Start agent execution using the correct Simple Agent WebSocket API.
        
        Args:
            instruction: Task instruction for the agent
            max_steps: Maximum number of steps to execute
            auto_continue: Number of steps to auto-continue (0 = manual)
            
        Returns:
            True if request sent successfully, False otherwise
        """
        if not self.connected:
            logger.error("Not connected to WebSocket server")
            return False
        
        try:
            # Use the correct event name based on Simple Agent WebSocket API
            await self.sio.emit('run_agent', {
                'instruction': instruction,
                'max_steps': max_steps,
                'auto_continue': auto_continue
            })
            logger.info(f"Started agent with instruction: {instruction}")
            return True
        except Exception as e:
            logger.error(f"Failed to start agent: {e}")
            return False
    
    async def stop_agent(self) -> bool:
        """
        Stop agent execution.
        
        Returns:
            True if request sent successfully, False otherwise
        """
        if not self.connected:
            logger.error("Not connected to WebSocket server")
            return False
        
        try:
            await self.sio.emit('stop_agent')
            logger.info("Sent stop agent request")
            return True
        except Exception as e:
            logger.error(f"Failed to stop agent: {e}")
            return False
    
    async def send_user_input(self, user_input: str) -> bool:
        """
        Send user input to the agent.
        
        Args:
            user_input: User's response/input
            
        Returns:
            True if request sent successfully, False otherwise
        """
        if not self.connected:
            logger.error("Not connected to WebSocket server")
            return False
        
        try:
            await self.sio.emit('user_input', {
                'input': user_input
            })
            logger.info(f"Sent user input: {user_input}")
            return True
        except Exception as e:
            logger.error(f"Failed to send user input: {e}")
            return False
    
    async def get_status(self) -> bool:
        """
        Get agent status.
        
        Returns:
            True if request sent successfully, False otherwise
        """
        if not self.connected:
            logger.error("Not connected to WebSocket server")
            return False
        
        try:
            await self.sio.emit('get_status')
            return True
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return False 