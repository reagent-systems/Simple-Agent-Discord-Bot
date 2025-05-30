"""
File Manager for Simple Agent Discord Bot

Handles tracking and sharing of files created during agent sessions.
"""

import aiohttp
import logging
import asyncio
import tempfile
import zipfile
import os
from typing import List, Dict, Optional
from pathlib import Path
import discord

logger = logging.getLogger(__name__)

class SessionFileManager:
    """Manages files created during a Simple Agent session."""
    
    def __init__(self, session_id: str, websocket_server_url: str, config=None):
        """
        Initialize the file manager.
        
        Args:
            session_id: Unique session identifier
            websocket_server_url: URL of the Simple Agent WebSocket server
            config: Configuration object for timeouts
        """
        self.session_id = session_id
        self.websocket_server_url = websocket_server_url.rstrip('/')
        self.created_files: List[Dict[str, str]] = []
        self.config = config
    
    def add_file(self, file_path: str, file_type: str = "file"):
        """
        Add a file to the tracking list.
        
        Args:
            file_path: Path of the created file
            file_type: Type of file (file, directory, etc.)
        """
        file_info = {
            'path': file_path,
            'type': file_type,
            'name': Path(file_path).name
        }
        
        # Avoid duplicates
        if file_info not in self.created_files:
            self.created_files.append(file_info)
            logger.debug(f"Added file to session {self.session_id}: {file_path}")
    
    async def download_file_content(self, file_path: str) -> Optional[bytes]:
        """
        Download file content as bytes from the Simple Agent server.
        
        Args:
            file_path: Relative path of the file to fetch
            
        Returns:
            File content as bytes or None if failed
        """
        if file_path == "Unknown file":
            logger.warning("Cannot fetch content for unknown file path")
            return None
            
        try:
            # Use the correct endpoint with relative_path
            content_url = f"{self.websocket_server_url}/sessions/{self.session_id}/files/{file_path}/content"
            
            async with aiohttp.ClientSession() as session:
                logger.debug(f"Downloading file content from: {content_url}")
                timeout_seconds = self.config.file_download_timeout if self.config else 30
                async with session.get(content_url, timeout=aiohttp.ClientTimeout(total=timeout_seconds)) as response:
                    if response.status == 200:
                        content = await response.read()  # Get as bytes
                        logger.info(f"Successfully downloaded file: {file_path} ({len(content)} bytes)")
                        return content
                    else:
                        logger.warning(f"HTTP {response.status} when downloading file: {file_path}")
                        return None
        
        except Exception as e:
            logger.error(f"Error downloading file {file_path}: {e}")
            return None
    
    async def create_temp_file(self, file_path: str, content: bytes) -> Optional[str]:
        """
        Create a temporary file with the given content.
        
        Args:
            file_path: Original file path (used for naming)
            content: File content as bytes
            
        Returns:
            Path to temporary file or None if failed
        """
        try:
            # Create temp file with original filename
            file_name = Path(file_path).name
            suffix = Path(file_path).suffix or '.txt'
            
            # Create temporary file
            fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=f"{file_name}_")
            
            with os.fdopen(fd, 'wb') as temp_file:
                temp_file.write(content)
            
            logger.debug(f"Created temporary file: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Error creating temp file for {file_path}: {e}")
            return None
    
    async def create_zip_file(self, temp_files: List[tuple]) -> Optional[str]:
        """
        Create a zip file containing all the temporary files.
        
        Args:
            temp_files: List of (temp_file_path, original_name) tuples
            
        Returns:
            Path to zip file or None if failed
        """
        try:
            # Create temp zip file
            fd, zip_path = tempfile.mkstemp(suffix='.zip', prefix=f'agent_files_{self.session_id}_')
            os.close(fd)  # Close the file descriptor so we can write to it
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for temp_path, original_name in temp_files:
                    if os.path.exists(temp_path):
                        zipf.write(temp_path, original_name)
                        logger.debug(f"Added {original_name} to zip")
            
            logger.info(f"Created zip file: {zip_path} with {len(temp_files)} files")
            return zip_path
            
        except Exception as e:
            logger.error(f"Error creating zip file: {e}")
            return None
    
    def cleanup_temp_files(self, file_paths: List[str]):
        """
        Clean up temporary files.
        
        Args:
            file_paths: List of file paths to delete
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.debug(f"Deleted temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {file_path}: {e}")
    
    async def send_files_to_thread(self, thread: discord.Thread) -> bool:
        """
        Download and send all tracked files to a Discord thread as attachments.
        
        Args:
            thread: Discord thread to send files to
            
        Returns:
            True if files were sent successfully, False otherwise
        """
        try:
            if not self.created_files:
                logger.debug(f"No files to send for session {self.session_id}")
                return True
            
            # Send summary embed first
            summary_embed = discord.Embed(
                title="📁 Files Created",
                description=f"The agent created {len(self.created_files)} file(s). Downloading and sharing them now...",
                color=discord.Color.green()
            )
            
            file_list = []
            for i, file_info in enumerate(self.created_files, 1):
                file_list.append(f"{i}. `{file_info['name']}`")
            
            summary_embed.add_field(
                name="Files",
                value="\n".join(file_list),
                inline=False
            )
            
            await thread.send(embed=summary_embed)
            file_delay = self.config.file_message_delay if self.config else 0.5
            await asyncio.sleep(file_delay)
            
            # Download all files
            temp_files = []
            failed_files = []
            
            for file_info in self.created_files:
                file_path = file_info['path']
                file_name = file_info['name']
                
                content = await self.download_file_content(file_path)
                if content is not None:
                    temp_path = await self.create_temp_file(file_path, content)
                    if temp_path:
                        temp_files.append((temp_path, file_name))
                    else:
                        failed_files.append(file_name)
                else:
                    failed_files.append(file_name)
            
            if not temp_files:
                await thread.send("❌ Failed to download any files from the agent.")
                return False
            
            # Decide whether to send individually or as zip
            total_size = sum(os.path.getsize(temp_path) for temp_path, _ in temp_files)
            max_file_size = 25 * 1024 * 1024  # 25MB Discord limit
            
            files_to_cleanup = [temp_path for temp_path, _ in temp_files]
            
            try:
                if len(temp_files) == 1 and total_size < max_file_size:
                    # Send single file
                    temp_path, file_name = temp_files[0]
                    file_attachment = discord.File(temp_path, filename=file_name)
                    await thread.send(f"📄 **{file_name}**", file=file_attachment)
                    
                elif len(temp_files) <= 10 and total_size < max_file_size:
                    # Send multiple files individually (Discord limit is 10 files per message)
                    attachments = []
                    for temp_path, file_name in temp_files:
                        attachments.append(discord.File(temp_path, filename=file_name))
                    
                    await thread.send("📦 **All created files:**", files=attachments)
                    
                else:
                    # Create zip file for many files or large total size
                    zip_path = await self.create_zip_file(temp_files)
                    if zip_path:
                        files_to_cleanup.append(zip_path)
                        
                        zip_size = os.path.getsize(zip_path)
                        if zip_size < max_file_size:
                            zip_attachment = discord.File(zip_path, filename=f"agent_files_{self.session_id}.zip")
                            await thread.send(f"🗜️ **All files zipped** ({len(temp_files)} files, {zip_size:,} bytes):", file=zip_attachment)
                        else:
                            await thread.send(f"❌ Files are too large to send (zip size: {zip_size:,} bytes, limit: {max_file_size:,} bytes)")
                    else:
                        await thread.send("❌ Failed to create zip file")
                
                # Report any failed files
                if failed_files:
                    failed_embed = discord.Embed(
                        title="⚠️ Some files could not be downloaded",
                        description="\n".join(f"• `{name}`" for name in failed_files),
                        color=discord.Color.orange()
                    )
                    await thread.send(embed=failed_embed)
            
            finally:
                # Always cleanup temp files
                self.cleanup_temp_files(files_to_cleanup)
            
            logger.info(f"Successfully sent {len(temp_files)} files to thread for session {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending files to thread for session {self.session_id}: {e}")
            return False
    
    def clear_files(self):
        """Clear all tracked files."""
        self.created_files.clear()
        logger.debug(f"Cleared files for session {self.session_id}")
    
    def get_file_count(self) -> int:
        """Get the number of tracked files."""
        return len(self.created_files) 