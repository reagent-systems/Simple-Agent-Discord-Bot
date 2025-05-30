#!/usr/bin/env python3
"""
Simple Agent Discord Bot - Main Entry Point

This bot integrates with the Simple Agent WebSocket system to provide
AI assistance through Discord slash commands.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

from bot.core.bot_client import SimpleAgentBot
from bot.utils.logger import setup_logging

def main():
    """Main entry point for the Discord bot."""
    # Load environment variables
    load_dotenv()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Get Discord token
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKEN environment variable is required!")
        return
    
    # Create and run the bot
    bot = SimpleAgentBot()
    
    try:
        logger.info("Starting Simple Agent Discord Bot...")
        bot.run(token)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed with error: {e}", exc_info=True)

if __name__ == "__main__":
    main() 