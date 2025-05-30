"""
Configuration Management

Handles loading and validating configuration from environment variables.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class Config:
    """Configuration manager for the Discord bot."""
    
    def __init__(self):
        """Load configuration from environment variables."""
        # Discord Configuration
        self.discord_token = os.getenv('DISCORD_TOKEN')
        self.discord_guild_id = self._get_optional_int('DISCORD_GUILD_ID')
        
        # WebSocket Configuration
        self.websocket_server_url = os.getenv('WEBSOCKET_SERVER_URL', 'http://localhost:5000')
        self.websocket_timeout = self._get_int('WEBSOCKET_TIMEOUT', 300)
        
        # Bot Configuration
        self.bot_prefix = os.getenv('BOT_PREFIX', '/')
        self.default_max_steps = int(os.getenv('DEFAULT_MAX_STEPS', '20'))
        self.default_auto_steps = int(os.getenv('DEFAULT_AUTO_STEPS', '10'))
        self.max_thread_messages = self._get_int('MAX_THREAD_MESSAGES', 50)
        
        # Logging Configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file = os.getenv('LOG_FILE', 'logs/discord_bot.log')
        
        # Timing configuration (in seconds)
        # Message rate limiting delays - controls delay between Discord messages
        self.message_delay = float(os.getenv('MESSAGE_DELAY', '0.3'))  # General message delay
        self.file_message_delay = float(os.getenv('FILE_MESSAGE_DELAY', '0.5'))  # File summary delay
        
        # Batching delays - controls how long to wait before sending batched notifications
        self.file_batch_delay = float(os.getenv('FILE_BATCH_DELAY', '2.0'))  # File creation batching
        self.tool_batch_delay = float(os.getenv('TOOL_BATCH_DELAY', '1.5'))  # Tool call batching
        
        # File download timeout - how long to wait for file downloads
        self.file_download_timeout = int(os.getenv('FILE_DOWNLOAD_TIMEOUT', '30'))
        
        # User input timeout - how long to wait for user responses (10 minutes default)
        self.user_input_timeout = int(os.getenv('USER_INPUT_TIMEOUT', '600'))
        
        # Validate required settings
        self._validate_config()
    
    def _get_int(self, key: str, default: int) -> int:
        """Get an integer value from environment variables."""
        try:
            value = os.getenv(key)
            return int(value) if value else default
        except ValueError:
            logger.warning(f"Invalid integer value for {key}, using default: {default}")
            return default
    
    def _get_optional_int(self, key: str) -> Optional[int]:
        """Get an optional integer value from environment variables."""
        try:
            value = os.getenv(key)
            return int(value) if value else None
        except ValueError:
            logger.warning(f"Invalid integer value for {key}, ignoring")
            return None
    
    def _validate_config(self):
        """Validate required configuration values."""
        if not self.discord_token:
            raise ValueError("DISCORD_TOKEN environment variable is required!")
        
        if not self.websocket_server_url:
            raise ValueError("WEBSOCKET_SERVER_URL environment variable is required!")
        
        # Validate ranges
        if self.default_max_steps <= 0:
            raise ValueError("DEFAULT_MAX_STEPS must be greater than 0")
        
        if self.default_auto_steps < 0:
            raise ValueError("DEFAULT_AUTO_STEPS must be 0 or greater")
        
        if self.websocket_timeout <= 0:
            raise ValueError("WEBSOCKET_TIMEOUT must be greater than 0")
    
    def get_websocket_url(self) -> str:
        """Get the full WebSocket URL."""
        base_url = self.websocket_server_url.rstrip('/')
        return f"{base_url}/socket.io/" 