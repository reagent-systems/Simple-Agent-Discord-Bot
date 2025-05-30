"""
Main Discord Bot Client

Handles Discord connection, slash commands, and bot lifecycle.
"""

import logging
import os
import discord
from discord.ext import commands
from typing import Optional

from bot.commands.simple_agent_command import SimpleAgentCommand
from bot.utils.config import Config

logger = logging.getLogger(__name__)

class SimpleAgentBot(commands.Bot):
    """Main Discord bot client for Simple Agent integration."""
    
    def __init__(self):
        """Initialize the bot with proper intents and configuration."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        super().__init__(
            command_prefix='/',
            intents=intents,
            help_command=None
        )
        
        self.config = Config()
        self.simple_agent_command = None
        
    async def setup_hook(self):
        """Setup hook called when the bot is ready to sync commands."""
        logger.info("Setting up bot...")
        
        # Add the simple agent command
        self.simple_agent_command = SimpleAgentCommand(self)
        await self.add_cog(self.simple_agent_command)
        
        # Sync commands to Discord
        guild_id = self.config.discord_guild_id
        if guild_id:
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Synced commands to guild {guild_id}")
        else:
            await self.tree.sync()
            logger.info("Synced commands globally")
    
    async def on_ready(self):
        """Called when the bot is ready and logged in."""
        logger.info(f"Bot is ready! Logged in as {self.user}")
        logger.info(f"Bot is in {len(self.guilds)} guilds")
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name="/simple_agent commands"
        )
        await self.change_presence(activity=activity)
    
    async def on_error(self, event_method: str, *args, **kwargs):
        """Handle bot errors."""
        logger.error(f"Error in {event_method}", exc_info=True)
    
    async def close(self):
        """Clean shutdown of the bot."""
        logger.info("Shutting down bot...")
        if self.simple_agent_command:
            await self.simple_agent_command.cleanup()
        await super().close() 