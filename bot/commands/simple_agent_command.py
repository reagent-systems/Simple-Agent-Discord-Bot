"""
Simple Agent Discord Command

Main slash command handler for Simple Agent integration.
"""

import asyncio
import logging
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict, Any

from bot.websocket.client import SimpleAgentWebSocketClient, AgentStatus
from bot.discord.thread_manager import ThreadManager
from bot.discord.message_formatter import MessageFormatter
from bot.utils.config import Config
from bot.utils.file_manager import SessionFileManager

logger = logging.getLogger(__name__)

class SimpleAgentCommand(commands.Cog):
    """Simple Agent slash command handler."""
    
    def __init__(self, bot: commands.Bot):
        """Initialize the command handler."""
        self.bot = bot
        self.config = Config()
        self.thread_manager = ThreadManager(bot, self.config)
        self.message_formatter = MessageFormatter()
        
        # Active sessions: session_id -> websocket_client
        self.active_sessions: Dict[str, SimpleAgentWebSocketClient] = {}
        
        # Session to thread mapping: session_id -> thread_id
        self.session_threads: Dict[str, int] = {}
        
        # File managers for each session: session_id -> SessionFileManager
        self.file_managers: Dict[str, SessionFileManager] = {}
        
        # File creation batching: session_id -> {'files': [...], 'task': asyncio.Task}
        self.file_batches: Dict[str, Dict] = {}
        
        # Tool call batching: session_id -> {'tools': [...], 'task': asyncio.Task}
        self.tool_batches: Dict[str, Dict] = {}
    
    @app_commands.command(
        name="simple_agent",
        description="Run a Simple Agent task with real-time updates"
    )
    @app_commands.describe(
        prompt="The task or instruction for the AI agent",
        max_steps="Maximum number of steps to execute (default: 20)",
        auto_steps="Number of steps to auto-continue without user confirmation (default: 10)"
    )
    async def simple_agent_command(
        self,
        interaction: discord.Interaction,
        prompt: str,
        max_steps: Optional[int] = None,
        auto_steps: Optional[int] = None
    ):
        """Handle the /simple_agent slash command."""
        # Set defaults
        if max_steps is None:
            max_steps = self.config.default_max_steps
        if auto_steps is None:
            auto_steps = self.config.default_auto_steps
        
        # Validate parameters
        if max_steps <= 0 or max_steps > 100:
            await interaction.response.send_message(
                "❌ max_steps must be between 1 and 100",
                ephemeral=True
            )
            return
        
        if auto_steps < 0 or auto_steps > max_steps:
            await interaction.response.send_message(
                f"❌ auto_steps must be between 0 and {max_steps}",
                ephemeral=True
            )
            return
        
        # Check if user already has an active session
        session_id = str(interaction.user.id)
        if session_id in self.active_sessions:
            await interaction.response.send_message(
                "❌ You already have an active Simple Agent session. Please wait for it to complete or stop it first.",
                ephemeral=True
            )
            return
        
        # Defer the response as this might take a moment
        await interaction.response.defer()
        
        try:
            # Create initial embed
            embed = self.message_formatter.create_task_embed(
                prompt=prompt,
                max_steps=max_steps,
                auto_steps=auto_steps,
                status="🔄 Connecting to Simple Agent..."
            )
            
            # Create thread for the session
            thread = await self.thread_manager.create_agent_thread(
                interaction.channel,
                f"Simple Agent: {prompt[:50]}...",
                interaction.user
            )
            
            if not thread:
                await interaction.followup.send(
                    "❌ Failed to create thread for the agent session",
                    ephemeral=True
                )
                return
            
            # Send initial message to thread
            initial_msg = await thread.send(embed=embed)
            
            # Update the original interaction with a nice embed
            starter_embed = discord.Embed(
                title="🚀 Simple Agent Session Started",
                description=f"Your AI agent is now running and will provide real-time updates in the thread below.",
                color=discord.Color.green()
            )
            starter_embed.add_field(
                name="📝 Task",
                value=f"```{prompt}```",
                inline=False
            )
            starter_embed.add_field(
                name="⚙️ Settings",
                value=f"• **Max Steps:** {max_steps}\n• **Auto Steps:** {auto_steps}",
                inline=True
            )
            starter_embed.add_field(
                name="🧵 Follow Progress",
                value=f"Click {thread.mention} to see real-time updates",
                inline=True
            )
            starter_embed.set_footer(text="The agent will create files and share them at the end of the session")
            
            await interaction.followup.send(embed=starter_embed)
            
            # Create WebSocket client
            ws_client = SimpleAgentWebSocketClient(
                self.config.get_websocket_url(),
                self.config.websocket_timeout
            )
            
            # Create file manager for this session
            file_manager = SessionFileManager(
                session_id,
                self.config.websocket_server_url,
                self.config
            )
            
            # Set up event handlers
            self._setup_websocket_handlers(ws_client, thread, initial_msg, session_id, file_manager)
            
            # Store session info
            self.active_sessions[session_id] = ws_client
            self.session_threads[session_id] = thread.id
            self.file_managers[session_id] = file_manager
            
            # Connect and start the agent with retry logic
            max_retries = 3
            retry_delay = 2  # seconds
            
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        # Update status to show retry attempt
                        retry_embed = self.message_formatter.create_status_embed(
                            f"🔄 Connection Attempt {attempt + 1}/{max_retries}",
                            "Retrying connection to Simple Agent server...",
                            discord.Color.orange()
                        )
                        await initial_msg.edit(embed=retry_embed)
                        await asyncio.sleep(retry_delay)
                    
                    if await ws_client.connect():
                        await ws_client.run_agent(prompt, max_steps, auto_steps)
                        break  # Success - exit retry loop
                    else:
                        if attempt == max_retries - 1:
                            # Final attempt failed
                            await thread.send("❌ Failed to connect to Simple Agent server after multiple attempts")
                            await self._cleanup_session(session_id)
                        # Continue to next retry attempt
                        
                except Exception as e:
                    logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        # Final attempt failed with exception
                        await thread.send(f"❌ Failed to connect to Simple Agent server: {str(e)}")
                        await self._cleanup_session(session_id)
                    # Continue to next retry attempt
        
        except Exception as e:
            logger.error(f"Error in simple_agent_command: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    def _setup_websocket_handlers(
        self,
        ws_client: SimpleAgentWebSocketClient,
        thread: discord.Thread,
        initial_msg: discord.Message,
        session_id: str,
        file_manager: SessionFileManager
    ):
        """Set up WebSocket event handlers for the session using correct Simple Agent events."""
        
        async def on_agent_started(data):
            # Update file manager with actual WebSocket session ID
            ws_session_id = data.get('session_id')
            if ws_session_id:
                file_manager.session_id = ws_session_id
                logger.info(f"Updated file manager session ID to: {ws_session_id}")
            
            embed = self.message_formatter.create_status_embed(
                "🚀 Agent Started",
                "The Simple Agent has started processing your request...",
                discord.Color.green()
            )
            await initial_msg.edit(embed=embed)
        
        async def on_step_start(data):
            step_num = data.get('step', data.get('step_number', '?'))
            embed = self.message_formatter.create_status_embed(
                f"🔄 Step {step_num}",
                "Processing step...",
                discord.Color.blue()
            )
            await thread.send(embed=embed)
            await asyncio.sleep(self.config.message_delay)
        
        async def on_assistant_message(data):
            message = data.get('message', data.get('content', ''))
            if message:
                embed = self.message_formatter.create_assistant_message_embed(message)
                await thread.send(embed=embed)
                await asyncio.sleep(self.config.message_delay)
        
        async def on_tool_call(data):
            # Get tool name from primary or alternative fields
            tool_name = data.get('function_name') or data.get('tool') or 'Unknown'
            
            # Get arguments from primary or alternative fields
            args = data.get('function_args') or data.get('parameters') or data.get('args') or {}
            
            # Format description based on available data
            description = data.get('description', 'Executing tool...')
            if args:
                if isinstance(args, dict):
                    args_str = ", ".join([f"{k}={v}" for k, v in args.items()])
                    description = f"Arguments: {args_str}"
                else:
                    description = str(args)
            
            # Log the data for debugging
            logger.debug(f"Tool call data: {data}")
            logger.debug(f"Parsed tool: {tool_name}, description: {description}")
            
            # Add to batch instead of sending immediately
            tool_info = {
                'tool_name': tool_name,
                'description': description
            }
            await self._add_tool_to_batch(session_id, thread, tool_info)
        
        async def on_tool_result(data):
            # Get result from primary or alternative fields
            result = data.get('result') or data.get('message') or 'Tool execution completed'
            
            # Get tool name if available
            tool_name = data.get('function_name') or data.get('tool') or 'Unknown Tool'
            
            # Get success status
            success = data.get('success', True)  # Default to True if not specified
            
            # Format result if it's a dict
            if isinstance(result, dict):
                result = result.get('content') or result.get('message') or str(result)
            
            # Truncate very long results
            if isinstance(result, str) and len(result) > 500:
                result = result[:497] + "..."
            
            # Log the data for debugging
            logger.debug(f"Tool result data: {data}")
            logger.debug(f"Parsed tool result: {tool_name}, success: {success}, result: {result}")
            
            embed = self.message_formatter.create_tool_result_embed(tool_name, result, success)
            await thread.send(embed=embed)
            await asyncio.sleep(self.config.message_delay)
        
        async def on_step_summary(data):
            summary = data.get('summary', data.get('content', ''))
            step_num = data.get('step', data.get('step_number', '?'))
            if summary:
                embed = self.message_formatter.create_step_summary_embed(step_num, summary)
                await thread.send(embed=embed)
                await asyncio.sleep(self.config.message_delay)
        
        async def on_final_summary(data):
            summary = data.get('summary', data.get('content', 'Task completed'))
            embed = self.message_formatter.create_completion_embed(summary)
            await thread.send(embed=embed)
            await asyncio.sleep(self.config.message_delay)
        
        async def on_file_created(data):
            # Update file manager session ID if provided in the event
            ws_session_id = data.get('session_id')
            if ws_session_id and file_manager.session_id != ws_session_id:
                file_manager.session_id = ws_session_id
                logger.info(f"Updated file manager session ID from file_created event: {ws_session_id}")
            
            # Handle both nested and flat file_created event formats
            file_path = None
            file_name = None
            
            # Format 1: Nested structure - check data.file first
            if 'file' in data and isinstance(data['file'], dict):
                file_info = data['file']
                file_path = file_info.get('relative_path') or file_info.get('path')
                file_name = file_info.get('name') or file_info.get('filename')
            
            # Format 2: Flat structure - check data directly
            if not file_path:
                file_path = data.get('relative_path') or data.get('path')
                if not file_name:
                    file_name = data.get('name') or data.get('filename')
            
            # If we only have a filename (no path), construct the path
            # Based on the tool calls, files are typically created in output/ directory
            if not file_path and file_name:
                file_path = f"output/{file_name}"
                logger.debug(f"Constructed file path from name: {file_name} -> {file_path}")
            
            # Use file_path as primary, fallback to name
            display_path = file_path or file_name or "Unknown file"
            
            # Final check - if still no path, warn and set to unknown
            if not file_path or file_path == "Unknown file":
                logger.warning(f"Could not extract or construct file path from file_created event: {data}")
                file_path = "Unknown file"
            
            # Track the file for later sharing
            file_manager.add_file(file_path)
            
            # Log the data for debugging
            logger.debug(f"File created data: {data}")
            logger.debug(f"Final file path: {file_path}, display: {display_path}")
            
            # Add to batch instead of sending immediately
            file_info = {
                'file_path': file_path,
                'display_path': display_path
            }
            await self._add_file_to_batch(session_id, thread, file_info)
        
        async def on_directory_changed(data):
            directory = data.get('path', data.get('directory', 'Unknown directory'))
            embed = self.message_formatter.create_status_embed(
                "📁 Directory Changed",
                f"Changed to directory: `{directory}`",
                discord.Color.orange()
            )
            await thread.send(embed=embed)
            await asyncio.sleep(self.config.message_delay)
        
        async def on_waiting_for_input(data):
            question = data.get('question', data.get('message', 'The agent is waiting for your input.'))
            embed = self.message_formatter.create_waiting_input_embed(question)
            
            # Add a note about who can respond
            user = self.bot.get_user(int(session_id))
            username = user.display_name if user else "the session owner"
            
            embed.add_field(
                name="👤 Who can respond?",
                value=f"Only **{username}** can provide input to continue the agent.",
                inline=False
            )
            embed.add_field(
                name="⏱️ Timeout",
                value="This will timeout in 10 minutes if no response is received.",
                inline=False
            )
            
            msg = await thread.send(embed=embed)
            await asyncio.sleep(self.config.message_delay)
            
            # Set up input collection
            await self._handle_user_input_request(thread, ws_client, session_id)
        
        async def on_task_completed(data):
            result = data.get('result', data.get('message', 'Task completed successfully!'))
            embed = self.message_formatter.create_completion_embed(result)
            await thread.send(embed=embed)
            await asyncio.sleep(self.config.message_delay)
        
        async def on_agent_finished(data):
            embed = self.message_formatter.create_status_embed(
                "✅ Agent Finished",
                "The Simple Agent has completed all tasks.",
                discord.Color.green()
            )
            await thread.send(embed=embed)
            await asyncio.sleep(self.config.message_delay)
            
            # Send all created files to the thread
            if file_manager.get_file_count() > 0:
                await file_manager.send_files_to_thread(thread)
            
            await self._cleanup_session(session_id)
        
        async def on_agent_error(data):
            error = data.get('error', data.get('message', 'An unknown error occurred'))
            embed = self.message_formatter.create_error_embed(error)
            await thread.send(embed=embed)
            await asyncio.sleep(self.config.message_delay)
            
            # Still send files if any were created before the error
            if file_manager.get_file_count() > 0:
                await file_manager.send_files_to_thread(thread)
            
            await self._cleanup_session(session_id)
        
        # Assign handlers to the WebSocket client
        ws_client.on_agent_started = on_agent_started
        ws_client.on_step_start = on_step_start
        ws_client.on_assistant_message = on_assistant_message
        ws_client.on_tool_call = on_tool_call
        ws_client.on_tool_result = on_tool_result
        ws_client.on_step_summary = on_step_summary
        ws_client.on_final_summary = on_final_summary
        ws_client.on_file_created = on_file_created
        ws_client.on_directory_changed = on_directory_changed
        ws_client.on_waiting_for_input = on_waiting_for_input
        ws_client.on_task_completed = on_task_completed
        ws_client.on_agent_finished = on_agent_finished
        ws_client.on_agent_error = on_agent_error
    
    async def _handle_user_input_request(
        self,
        thread: discord.Thread,
        ws_client: SimpleAgentWebSocketClient,
        session_id: str
    ):
        """Handle user input request from the agent."""
        def check(message):
            return (
                message.channel == thread and
                message.author.id == int(session_id) and
                not message.author.bot
            )
        
        # Track messages from other users to provide feedback
        other_user_messages = []
        
        def other_user_check(message):
            return (
                message.channel == thread and
                message.author.id != int(session_id) and
                not message.author.bot
            )
        
        try:
            while True:
                # Wait for either the correct user or any other user
                done, pending = await asyncio.wait([
                    asyncio.create_task(self.bot.wait_for('message', check=check, timeout=self.config.user_input_timeout)),
                    asyncio.create_task(self.bot.wait_for('message', check=other_user_check, timeout=1))
                ], return_when=asyncio.FIRST_COMPLETED)
                
                # Cancel pending tasks
                for task in pending:
                    task.cancel()
                
                # Check which task completed
                completed_task = done.pop()
                
                try:
                    response = await completed_task
                    
                    # Check if this was the correct user
                    if response.author.id == int(session_id):
                        # Correct user responded
                        await ws_client.send_user_input(response.content)
                        await response.add_reaction('✅')
                        
                        # Acknowledge the input with an embed
                        ack_embed = discord.Embed(
                            title="✅ Input Received",
                            description=f"Your input has been sent to the agent: `{response.content}`",
                            color=discord.Color.green()
                        )
                        await thread.send(embed=ack_embed)
                        break
                    else:
                        # Wrong user tried to respond
                        await response.add_reaction('❌')
                        user = self.bot.get_user(int(session_id))
                        username = user.display_name if user else "the session owner"
                        
                        warning_embed = discord.Embed(
                            title="❌ Unauthorized Input",
                            description=f"Only **{username}** can provide input for this agent session.",
                            color=discord.Color.red()
                        )
                        warning_msg = await thread.send(embed=warning_embed)
                        
                        # Delete the warning after 10 seconds
                        await asyncio.sleep(10)
                        try:
                            await warning_msg.delete()
                        except:
                            pass  # Ignore if already deleted
                
                except asyncio.TimeoutError:
                    # No messages from other users, continue waiting
                    continue
                except Exception as e:
                    logger.error(f"Error in user input handling: {e}")
                    continue
            
        except asyncio.TimeoutError:
            embed = self.message_formatter.create_error_embed(
                "⏰ Input timeout - session will be terminated"
            )
            await thread.send(embed=embed)
            await ws_client.stop_agent()
            await self._cleanup_session(session_id)
    
    async def _cleanup_session(self, session_id: str):
        """Clean up a finished session."""
        if session_id in self.active_sessions:
            ws_client = self.active_sessions[session_id]
            await ws_client.disconnect()
            del self.active_sessions[session_id]
        
        if session_id in self.session_threads:
            del self.session_threads[session_id]
        
        if session_id in self.file_managers:
            self.file_managers[session_id].clear_files()
            del self.file_managers[session_id]
        
        # Clean up any pending file batches
        if session_id in self.file_batches:
            batch_info = self.file_batches[session_id]
            if batch_info.get('task') and not batch_info['task'].done():
                batch_info['task'].cancel()
            del self.file_batches[session_id]
        
        # Clean up any pending tool batches
        if session_id in self.tool_batches:
            batch_info = self.tool_batches[session_id]
            if batch_info.get('task') and not batch_info['task'].done():
                batch_info['task'].cancel()
            del self.tool_batches[session_id]
        
        logger.info(f"Cleaned up session {session_id}")
    
    @app_commands.command(
        name="stop_agent",
        description="Stop your active Simple Agent session"
    )
    async def stop_agent_command(self, interaction: discord.Interaction):
        """Stop the user's active agent session."""
        session_id = str(interaction.user.id)
        
        if session_id not in self.active_sessions:
            await interaction.response.send_message(
                "❌ You don't have an active Simple Agent session",
                ephemeral=True
            )
            return
        
        ws_client = self.active_sessions[session_id]
        await ws_client.stop_agent()
        
        await interaction.response.send_message(
            "🛑 Stop request sent to your Simple Agent session",
            ephemeral=True
        )
    
    @app_commands.command(
        name="agent_status",
        description="Check the status of your Simple Agent session"
    )
    async def agent_status_command(self, interaction: discord.Interaction):
        """Check the status of the user's agent session."""
        session_id = str(interaction.user.id)
        
        if session_id not in self.active_sessions:
            await interaction.response.send_message(
                "❌ You don't have an active Simple Agent session",
                ephemeral=True
            )
            return
        
        ws_client = self.active_sessions[session_id]
        thread_id = self.session_threads.get(session_id)
        file_manager = self.file_managers.get(session_id)
        
        status_text = {
            AgentStatus.IDLE: "⏸️ Idle",
            AgentStatus.RUNNING: "🔄 Running",
            AgentStatus.WAITING_INPUT: "⏳ Waiting for Input",
            AgentStatus.COMPLETED: "✅ Completed",
            AgentStatus.ERROR: "❌ Error"
        }.get(ws_client.status, "❓ Unknown")
        
        thread_mention = f"<#{thread_id}>" if thread_id else "Unknown"
        file_count = file_manager.get_file_count() if file_manager else 0
        
        embed = discord.Embed(
            title="🤖 Agent Status",
            color=discord.Color.blue()
        )
        embed.add_field(name="Status", value=status_text, inline=True)
        embed.add_field(name="Thread", value=thread_mention, inline=True)
        embed.add_field(name="Connected", value="✅ Yes" if ws_client.connected else "❌ No", inline=True)
        embed.add_field(name="Files Created", value=str(file_count), inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def cleanup(self):
        """Cleanup all active sessions."""
        logger.info("Cleaning up all active Simple Agent sessions...")
        
        for session_id in list(self.active_sessions.keys()):
            await self._cleanup_session(session_id)
        
        logger.info("All sessions cleaned up")
    
    async def _send_batched_file_notification(self, session_id: str, thread: discord.Thread):
        """Send a batched notification for multiple file creations."""
        if session_id not in self.file_batches:
            return
        
        batch_info = self.file_batches[session_id]
        files = batch_info.get('files', [])
        
        if not files:
            return
        
        try:
            if len(files) == 1:
                # Single file - send individual notification
                file_info = files[0]
                embed = self.message_formatter.create_status_embed(
                    "📄 File Created",
                    f"Created file: `{file_info['display_path']}`",
                    discord.Color.purple()
                )
                await thread.send(embed=embed)
            else:
                # Multiple files - send batch notification
                file_list = []
                for file_info in files[:10]:  # Show max 10 files in preview
                    file_list.append(f"• `{file_info['display_path']}`")
                
                if len(files) > 10:
                    file_list.append(f"• ... and {len(files) - 10} more files")
                
                embed = self.message_formatter.create_status_embed(
                    f"📁 Created {len(files)} Files",
                    "\n".join(file_list),
                    discord.Color.purple()
                )
                await thread.send(embed=embed)
            
            # Clear the batch
            del self.file_batches[session_id]
            
        except Exception as e:
            logger.error(f"Error sending batched file notification: {e}")
    
    async def _add_file_to_batch(self, session_id: str, thread: discord.Thread, file_info: dict):
        """Add a file to the batch and handle timing."""
        # Initialize batch if not exists
        if session_id not in self.file_batches:
            self.file_batches[session_id] = {'files': [], 'task': None}
        
        batch_info = self.file_batches[session_id]
        batch_info['files'].append(file_info)
        
        # Cancel existing timer
        if batch_info['task'] and not batch_info['task'].done():
            batch_info['task'].cancel()
        
        # Set new timer for batch sending (2 seconds)
        async def send_after_delay():
            await asyncio.sleep(self.config.file_batch_delay)
            await self._send_batched_file_notification(session_id, thread)
        
        batch_info['task'] = asyncio.create_task(send_after_delay())
    
    async def _send_batched_tool_notification(self, session_id: str, thread: discord.Thread):
        """Send a batched notification for multiple tool calls."""
        if session_id not in self.tool_batches:
            return
        
        batch_info = self.tool_batches[session_id]
        tools = batch_info.get('tools', [])
        
        if not tools:
            return
        
        try:
            if len(tools) == 1:
                # Single tool - send individual notification
                tool_info = tools[0]
                embed = self.message_formatter.create_tool_call_embed(
                    tool_info['tool_name'], 
                    tool_info['description']
                )
                await thread.send(embed=embed)
            else:
                # Multiple tools - send batch notification
                tool_list = []
                for tool_info in tools[:8]:  # Show max 8 tools in preview
                    tool_name = tool_info['tool_name']
                    # Truncate long descriptions for batch view
                    desc = tool_info['description']
                    if len(desc) > 50:
                        desc = desc[:47] + "..."
                    tool_list.append(f"• **{tool_name}**: {desc}")
                
                if len(tools) > 8:
                    tool_list.append(f"• ... and {len(tools) - 8} more tools")
                
                embed = self.message_formatter.create_status_embed(
                    f"🔧 Executed {len(tools)} Tools",
                    "\n".join(tool_list),
                    discord.Color.blue()
                )
                await thread.send(embed=embed)
            
            # Clear the batch
            del self.tool_batches[session_id]
            
        except Exception as e:
            logger.error(f"Error sending batched tool notification: {e}")
    
    async def _add_tool_to_batch(self, session_id: str, thread: discord.Thread, tool_info: dict):
        """Add a tool call to the batch and handle timing."""
        # Initialize batch if not exists
        if session_id not in self.tool_batches:
            self.tool_batches[session_id] = {'tools': [], 'task': None}
        
        batch_info = self.tool_batches[session_id]
        batch_info['tools'].append(tool_info)
        
        # Cancel existing timer
        if batch_info['task'] and not batch_info['task'].done():
            batch_info['task'].cancel()
        
        # Set new timer for batch sending (1.5 seconds - shorter than files since tools are quicker)
        async def send_after_delay():
            await asyncio.sleep(self.config.tool_batch_delay)
            await self._send_batched_tool_notification(session_id, thread)
        
        batch_info['task'] = asyncio.create_task(send_after_delay()) 