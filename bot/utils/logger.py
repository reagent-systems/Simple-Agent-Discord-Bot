"""
Logging Configuration

Sets up structured logging for the Discord bot.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path

def setup_logging(log_level: str = None, log_file: str = None):
    """
    Set up logging configuration for the bot.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
    """
    # Get configuration from environment if not provided
    if log_level is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO')
    if log_file is None:
        log_file = os.getenv('LOG_FILE', 'logs/discord_bot.log')
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Console handler with UTF-8 encoding
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    
    # Ensure UTF-8 encoding for Windows
    if hasattr(console_handler.stream, 'reconfigure'):
        console_handler.stream.reconfigure(encoding='utf-8')
    
    root_logger.addHandler(console_handler)
    
    # File handler with rotation and UTF-8 encoding
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'  # Explicit UTF-8 encoding for file
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Reduce noise from discord.py
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    
    # Reduce noise from socketio
    logging.getLogger('socketio').setLevel(logging.WARNING)
    logging.getLogger('engineio').setLevel(logging.WARNING)
    
    logging.info("Logging configured successfully") 