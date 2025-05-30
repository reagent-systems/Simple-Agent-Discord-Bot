"""
Discord Thread Manager

Handles creation and management of Discord threads for agent sessions.
"""

import logging
import discord
from discord.ext import commands
from typing import Optional, Union

from bot.utils.config import Config

logger = logging.getLogger(__name__)

class ThreadManager:
    """Manages Discord threads for Simple Agent sessions."""
    
    def __init__(self, bot: commands.Bot, config: Config):
        """Initialize the thread manager."""
        self.bot = bot
        self.config = config
    
    async def create_agent_thread(
        self,
        channel: Union[discord.TextChannel, discord.Thread],
        thread_name: str,
        user: discord.User
    ) -> Optional[discord.Thread]:
        """
        Create a thread for an agent session.
        
        Args:
            channel: Channel to create the thread in
            thread_name: Name for the thread
            user: User who initiated the session
            
        Returns:
            Created thread or None if failed
        """
        try:
            # If the channel is already a thread, we can't create a subthread
            if isinstance(channel, discord.Thread):
                logger.warning("Cannot create thread within a thread, using existing thread")
                return channel
            
            # Ensure we have a text channel
            if not isinstance(channel, discord.TextChannel):
                logger.error(f"Cannot create thread in channel type: {type(channel)}")
                return None
            
            # Check permissions
            permissions = channel.permissions_for(channel.guild.me)
            if not permissions.create_public_threads:
                logger.error("Bot lacks permission to create public threads")
                return None
            
            # Create the thread
            thread = await channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.public_thread,
                reason=f"Simple Agent session for {user.display_name}"
            )
            
            logger.info(f"Created thread '{thread_name}' (ID: {thread.id}) for user {user.display_name}")
            
            # Add the user to the thread
            try:
                await thread.add_user(user)
            except discord.HTTPException as e:
                logger.warning(f"Could not add user to thread: {e}")
            
            return thread
            
        except discord.Forbidden:
            logger.error("Bot lacks permission to create threads")
            return None
        except discord.HTTPException as e:
            logger.error(f"Failed to create thread: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating thread: {e}", exc_info=True)
            return None
    
    async def cleanup_thread(self, thread: discord.Thread, reason: str = "Session completed"):
        """
        Clean up a thread after session completion.
        
        Args:
            thread: Thread to clean up
            reason: Reason for cleanup
        """
        try:
            # Archive the thread instead of deleting it
            if not thread.archived:
                await thread.edit(archived=True, reason=reason)
                logger.info(f"Archived thread {thread.name} (ID: {thread.id}): {reason}")
        
        except discord.Forbidden:
            logger.warning(f"Cannot archive thread {thread.id}: Missing permissions")
        except discord.HTTPException as e:
            logger.error(f"Failed to archive thread {thread.id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error archiving thread {thread.id}: {e}", exc_info=True)
    
    async def send_thread_update(
        self,
        thread: discord.Thread,
        content: str = None,
        embed: discord.Embed = None
    ) -> Optional[discord.Message]:
        """
        Send an update message to a thread.
        
        Args:
            thread: Thread to send message to
            content: Text content of the message
            embed: Embed to send
            
        Returns:
            Sent message or None if failed
        """
        try:
            # Check message limits
            if await self._check_message_limit(thread):
                return None
            
            message = await thread.send(content=content, embed=embed)
            return message
            
        except discord.Forbidden:
            logger.error(f"Cannot send message to thread {thread.id}: Missing permissions")
            return None
        except discord.HTTPException as e:
            logger.error(f"Failed to send message to thread {thread.id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error sending message to thread {thread.id}: {e}", exc_info=True)
            return None
    
    async def _check_message_limit(self, thread: discord.Thread) -> bool:
        """
        Check if the thread has reached the message limit.
        
        Args:
            thread: Thread to check
            
        Returns:
            True if limit reached, False otherwise
        """
        try:
            message_count = 0
            async for _ in thread.history(limit=self.config.max_thread_messages + 1):
                message_count += 1
                if message_count > self.config.max_thread_messages:
                    logger.warning(f"Thread {thread.id} has reached message limit ({self.config.max_thread_messages})")
                    
                    # Send a warning message
                    embed = discord.Embed(
                        title="⚠️ Message Limit Reached",
                        description=f"This thread has reached the maximum message limit of {self.config.max_thread_messages}. No more updates will be posted.",
                        color=discord.Color.orange()
                    )
                    await thread.send(embed=embed)
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking message limit for thread {thread.id}: {e}")
            return False
    
    def format_thread_name(self, prompt: str, max_length: int = 100) -> str:
        """
        Format a thread name from a prompt.
        
        Args:
            prompt: Original prompt
            max_length: Maximum length for thread name
            
        Returns:
            Formatted thread name
        """
        # Clean the prompt
        clean_prompt = prompt.strip()
        
        # Truncate if too long
        if len(clean_prompt) > max_length - 15:  # Leave space for "Simple Agent: "
            clean_prompt = clean_prompt[:max_length - 18] + "..."
        
        return f"Simple Agent: {clean_prompt}" 