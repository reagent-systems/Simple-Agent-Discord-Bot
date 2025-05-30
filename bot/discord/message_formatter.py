"""
Discord Message Formatter

Handles formatting of Discord embeds for Simple Agent events.
"""

import discord
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class MessageFormatter:
    """Formats Discord messages and embeds for Simple Agent events."""
    
    def __init__(self):
        """Initialize the message formatter."""
        self.colors = {
            'primary': discord.Color.blue(),
            'success': discord.Color.green(),
            'warning': discord.Color.orange(),
            'error': discord.Color.red(),
            'info': discord.Color.blurple(),
            'tool': discord.Color.purple(),
            'assistant': discord.Color.gold()
        }
    
    def create_task_embed(
        self,
        prompt: str,
        max_steps: int,
        auto_steps: int,
        status: str
    ) -> discord.Embed:
        """
        Create an embed for a new task.
        
        Args:
            prompt: Task prompt
            max_steps: Maximum steps
            auto_steps: Auto continue steps
            status: Current status
            
        Returns:
            Discord embed
        """
        embed = discord.Embed(
            title="🤖 Simple Agent Task",
            description=f"**Prompt:** {prompt}",
            color=self.colors['primary'],
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Max Steps", value=str(max_steps), inline=True)
        embed.add_field(name="Auto Steps", value=str(auto_steps), inline=True)
        embed.add_field(name="Status", value=status, inline=True)
        
        embed.set_footer(text="Simple Agent Discord Bot")
        
        return embed
    
    def create_status_embed(
        self,
        title: str,
        description: str,
        color: discord.Color = None
    ) -> discord.Embed:
        """
        Create a status embed.
        
        Args:
            title: Embed title
            description: Embed description
            color: Embed color
            
        Returns:
            Discord embed
        """
        if color is None:
            color = self.colors['info']
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        
        return embed
    
    def create_assistant_message_embed(self, message: str) -> discord.Embed:
        """
        Create an embed for assistant messages.
        
        Args:
            message: Assistant message content
            
        Returns:
            Discord embed
        """
        # Truncate long messages
        if len(message) > 2000:
            message = message[:1997] + "..."
        
        embed = discord.Embed(
            title="🧠 Assistant Response",
            description=message,
            color=self.colors['assistant'],
            timestamp=datetime.utcnow()
        )
        
        return embed
    
    def create_tool_call_embed(self, tool_name: str, description: str) -> discord.Embed:
        """
        Create an embed for tool calls.
        
        Args:
            tool_name: Name of the tool being called
            description: Description of the tool call
            
        Returns:
            Discord embed
        """
        embed = discord.Embed(
            title=f"🔧 Tool: {tool_name}",
            description=description,
            color=self.colors['tool'],
            timestamp=datetime.utcnow()
        )
        
        return embed
    
    def create_tool_result_embed(self, tool_name: str, result: str, success: bool = True) -> discord.Embed:
        """
        Create an embed for tool results.
        
        Args:
            tool_name: Name of the tool that executed
            result: Result of the tool execution
            success: Whether the tool execution was successful
            
        Returns:
            Discord embed
        """
        # Choose emoji and color based on success
        if success:
            emoji = "✅"
            color = self.colors['success']
        else:
            emoji = "❌"
            color = self.colors['error']
        
        embed = discord.Embed(
            title=f"{emoji} {tool_name} Result",
            description=str(result),
            color=color,
            timestamp=datetime.utcnow()
        )
        
        return embed
    
    def create_step_summary_embed(self, step_num: str, summary: str) -> discord.Embed:
        """
        Create an embed for step summaries.
        
        Args:
            step_num: Step number
            summary: Step summary
            
        Returns:
            Discord embed
        """
        # Truncate long summaries
        if len(summary) > 1500:
            summary = summary[:1497] + "..."
        
        embed = discord.Embed(
            title=f"📝 Step {step_num} Summary",
            description=summary,
            color=self.colors['success'],
            timestamp=datetime.utcnow()
        )
        
        return embed
    
    def create_waiting_input_embed(self, question: str) -> discord.Embed:
        """
        Create an embed for waiting for user input.
        
        Args:
            question: Question or prompt for the user
            
        Returns:
            Discord embed
        """
        embed = discord.Embed(
            title="⏳ Waiting for Your Input",
            description=f"**The agent is asking:**\n{question}\n\n*Please reply in this thread to continue...*",
            color=self.colors['warning'],
            timestamp=datetime.utcnow()
        )
        
        return embed
    
    def create_completion_embed(self, result: str) -> discord.Embed:
        """
        Create an embed for task completion.
        
        Args:
            result: Task completion result
            
        Returns:
            Discord embed
        """
        # Truncate long results
        if len(result) > 1500:
            result = result[:1497] + "..."
        
        embed = discord.Embed(
            title="✅ Task Completed",
            description=result,
            color=self.colors['success'],
            timestamp=datetime.utcnow()
        )
        
        return embed
    
    def create_error_embed(self, error: str) -> discord.Embed:
        """
        Create an embed for errors.
        
        Args:
            error: Error message
            
        Returns:
            Discord embed
        """
        # Truncate long error messages
        if len(error) > 1500:
            error = error[:1497] + "..."
        
        embed = discord.Embed(
            title="❌ Error",
            description=error,
            color=self.colors['error'],
            timestamp=datetime.utcnow()
        )
        
        return embed
    
    def create_progress_embed(
        self,
        current_step: int,
        total_steps: int,
        status: str,
        details: Optional[str] = None
    ) -> discord.Embed:
        """
        Create a progress embed.
        
        Args:
            current_step: Current step number
            total_steps: Total number of steps
            status: Current status
            details: Additional details
            
        Returns:
            Discord embed
        """
        progress_percentage = (current_step / total_steps) * 100 if total_steps > 0 else 0
        progress_bar = self._create_progress_bar(progress_percentage)
        
        embed = discord.Embed(
            title="📊 Agent Progress",
            color=self.colors['info'],
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Progress",
            value=f"{progress_bar} {progress_percentage:.1f}%",
            inline=False
        )
        
        embed.add_field(name="Step", value=f"{current_step}/{total_steps}", inline=True)
        embed.add_field(name="Status", value=status, inline=True)
        
        if details:
            embed.add_field(name="Details", value=details, inline=False)
        
        return embed
    
    def _create_progress_bar(self, percentage: float, length: int = 20) -> str:
        """
        Create a text-based progress bar.
        
        Args:
            percentage: Progress percentage (0-100)
            length: Length of the progress bar
            
        Returns:
            Progress bar string
        """
        filled_length = int(length * percentage / 100)
        bar = '█' * filled_length + '░' * (length - filled_length)
        return f"`{bar}`"
    
    def truncate_text(self, text: str, max_length: int = 2000) -> str:
        """
        Truncate text to fit Discord limits.
        
        Args:
            text: Text to truncate
            max_length: Maximum length
            
        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        
        return text[:max_length - 3] + "..."
    
    def format_code_block(self, content: str, language: str = "") -> str:
        """
        Format content as a Discord code block.
        
        Args:
            content: Content to format
            language: Programming language for syntax highlighting
            
        Returns:
            Formatted code block
        """
        # Ensure content fits in Discord message limits
        max_content_length = 1990 - len(language) - 6  # Account for ```language\n and ```
        
        if len(content) > max_content_length:
            content = content[:max_content_length - 3] + "..."
        
        return f"```{language}\n{content}\n```" 