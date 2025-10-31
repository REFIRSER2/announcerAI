"""Discord Bot implementation for LoL Announcer AI.

This module provides the main Discord bot class that handles:
- Voice channel management (join/leave)
- Command processing (!join, !leave, !status)
- Screen share stream detection and frame capture
- TTS audio playback from queue
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path

import discord
from discord.ext import commands, tasks

from .stream_capture import StreamCapture
from .audio_player import AudioPlayer


logger = logging.getLogger(__name__)


class AnnouncerBot(commands.Bot):
    """Discord bot for LoL game announcements.

    This bot connects to Discord voice channels, captures screen share streams,
    extracts frames for analysis, and plays TTS-generated audio announcements.

    Attributes:
        frame_queue: Async queue for captured frames to be sent to vision analyzer
        audio_queue: Async queue for TTS audio files to be played
        stream_capture: Handler for capturing frames from screen share
        audio_player: Handler for playing TTS audio in voice channel
        voice_clients: Dict of guild_id -> voice_client connections
    """

    def __init__(
        self,
        command_prefix: str = "!",
        frame_queue: Optional[asyncio.Queue] = None,
        audio_queue: Optional[asyncio.Queue] = None,
        frame_rate: float = 1.0,
        intents: Optional[discord.Intents] = None,
        **kwargs: Any
    ):
        """Initialize the AnnouncerBot.

        Args:
            command_prefix: Command prefix for bot commands (default: "!")
            frame_queue: Queue to put captured frames into
            audio_queue: Queue to get TTS audio files from
            frame_rate: Frames per second to capture (default: 1.0)
            intents: Discord intents for the bot
            **kwargs: Additional arguments passed to commands.Bot
        """
        if intents is None:
            intents = discord.Intents.default()
            intents.message_content = True
            intents.voice_states = True
            intents.guilds = True

        super().__init__(command_prefix=command_prefix, intents=intents, **kwargs)

        # Queues for inter-module communication
        self.frame_queue = frame_queue or asyncio.Queue(maxsize=100)
        self.audio_queue = audio_queue or asyncio.Queue(maxsize=50)

        # Stream and audio handlers
        self.stream_capture = StreamCapture(frame_rate=frame_rate)
        self.audio_player = AudioPlayer()

        # Track voice connections per guild
        self.voice_clients: Dict[int, discord.VoiceClient] = {}

        # Register commands
        self._register_commands()

        logger.info(
            f"AnnouncerBot initialized with prefix '{command_prefix}', "
            f"frame_rate={frame_rate}"
        )

    def _register_commands(self) -> None:
        """Register bot commands."""

        @self.command(name="join", help="Join your current voice channel")
        async def join(ctx: commands.Context) -> None:
            """Join the voice channel of the command author."""
            await self._handle_join(ctx)

        @self.command(name="leave", help="Leave the current voice channel")
        async def leave(ctx: commands.Context) -> None:
            """Leave the voice channel in the current guild."""
            await self._handle_leave(ctx)

        @self.command(name="status", help="Show bot status and connection info")
        async def status(ctx: commands.Context) -> None:
            """Display current bot status."""
            await self._handle_status(ctx)

    async def on_ready(self) -> None:
        """Called when the bot successfully connects to Discord."""
        logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")

        # Start background tasks
        self.frame_processor_task.start()
        self.audio_player_task.start()

        logger.info("Background tasks started")

    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError
    ) -> None:
        """Handle command errors.

        Args:
            ctx: Command context
            error: The error that occurred
        """
        logger.error(f"Command error in {ctx.command}: {error}", exc_info=error)

        if isinstance(error, commands.CommandNotFound):
            await ctx.send("Command not found. Use `!help` for available commands.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing argument: {error.param.name}")
        else:
            await ctx.send(f"An error occurred: {str(error)}")

    async def _handle_join(self, ctx: commands.Context) -> None:
        """Handle the !join command.

        Args:
            ctx: Command context
        """
        try:
            # Check if user is in a voice channel
            if not ctx.author.voice:
                await ctx.send("You must be in a voice channel to use this command.")
                return

            channel = ctx.author.voice.channel
            guild_id = ctx.guild.id

            # Check if already connected
            if guild_id in self.voice_clients and self.voice_clients[guild_id].is_connected():
                await ctx.send(f"Already connected to {self.voice_clients[guild_id].channel.name}")
                return

            # Connect to voice channel
            voice_client = await channel.connect()
            self.voice_clients[guild_id] = voice_client

            logger.info(f"Connected to voice channel: {channel.name} (Guild: {ctx.guild.name})")
            await ctx.send(f"Joined {channel.name}! Ready to analyze and announce.")

            # Start monitoring for screen shares
            asyncio.create_task(self._monitor_screen_share(guild_id))

        except Exception as e:
            logger.error(f"Error joining voice channel: {e}", exc_info=True)
            await ctx.send(f"Failed to join voice channel: {str(e)}")

    async def _handle_leave(self, ctx: commands.Context) -> None:
        """Handle the !leave command.

        Args:
            ctx: Command context
        """
        try:
            guild_id = ctx.guild.id

            if guild_id not in self.voice_clients:
                await ctx.send("Not connected to any voice channel.")
                return

            voice_client = self.voice_clients[guild_id]

            # Stop any ongoing audio playback
            if voice_client.is_playing():
                voice_client.stop()

            # Disconnect
            await voice_client.disconnect()
            del self.voice_clients[guild_id]

            logger.info(f"Disconnected from voice channel (Guild: {ctx.guild.name})")
            await ctx.send("Left the voice channel.")

        except Exception as e:
            logger.error(f"Error leaving voice channel: {e}", exc_info=True)
            await ctx.send(f"Failed to leave voice channel: {str(e)}")

    async def _handle_status(self, ctx: commands.Context) -> None:
        """Handle the !status command.

        Args:
            ctx: Command context
        """
        try:
            guild_id = ctx.guild.id

            # Build status message
            status_lines = [
                f"**Bot Status**",
                f"Connected to: {len(self.voice_clients)} voice channel(s)",
                f"Frame queue size: {self.frame_queue.qsize()}/{self.frame_queue.maxsize}",
                f"Audio queue size: {self.audio_queue.qsize()}/{self.audio_queue.maxsize}",
            ]

            if guild_id in self.voice_clients:
                voice_client = self.voice_clients[guild_id]
                status_lines.append(f"Current channel: {voice_client.channel.name}")
                status_lines.append(f"Playing audio: {voice_client.is_playing()}")
            else:
                status_lines.append("Not connected to voice channel in this server")

            await ctx.send("\n".join(status_lines))

        except Exception as e:
            logger.error(f"Error getting status: {e}", exc_info=True)
            await ctx.send(f"Failed to get status: {str(e)}")

    async def _monitor_screen_share(self, guild_id: int) -> None:
        """Monitor voice channel for screen share streams and capture frames.

        Args:
            guild_id: The guild ID to monitor
        """
        logger.info(f"Starting screen share monitoring for guild {guild_id}")

        try:
            while guild_id in self.voice_clients:
                voice_client = self.voice_clients[guild_id]

                # Check if still connected
                if not voice_client.is_connected():
                    logger.warning(f"Voice client disconnected for guild {guild_id}")
                    break

                # Look for users sharing screen
                for member in voice_client.channel.members:
                    if member.voice and member.voice.self_video:
                        logger.info(f"Detected screen share from {member.name}")

                        # Capture frames from the stream
                        # Note: Discord.py doesn't directly expose screen share streams
                        # This would require custom implementation using Discord's WebRTC
                        # For now, this is a placeholder for the functionality
                        await self._capture_stream_frames(member, guild_id)

                await asyncio.sleep(1)  # Check every second

        except Exception as e:
            logger.error(f"Error monitoring screen share: {e}", exc_info=True)
        finally:
            logger.info(f"Stopped screen share monitoring for guild {guild_id}")

    async def _capture_stream_frames(
        self,
        member: discord.Member,
        guild_id: int
    ) -> None:
        """Capture frames from a member's screen share stream.

        Note: This is a placeholder implementation. Actual Discord screen share
        capture would require custom WebRTC implementation or Discord API extensions.

        Args:
            member: The member sharing their screen
            guild_id: The guild ID
        """
        try:
            # This would be implemented with actual stream capture logic
            # For now, this is a conceptual placeholder
            logger.debug(f"Capturing frames from {member.name}'s stream")

            # Placeholder: In real implementation, this would:
            # 1. Connect to the WebRTC stream
            # 2. Capture frames at the configured rate
            # 3. Put frames into the frame_queue

            # Example of putting a frame into queue:
            # frame = await self.stream_capture.capture_frame(stream)
            # if frame is not None:
            #     await self.frame_queue.put({
            #         'frame': frame,
            #         'timestamp': asyncio.get_event_loop().time(),
            #         'member': member.name,
            #         'guild_id': guild_id
            #     })

        except Exception as e:
            logger.error(f"Error capturing stream frames: {e}", exc_info=True)

    @tasks.loop(seconds=0.1)
    async def frame_processor_task(self) -> None:
        """Background task to process frames from screen share streams."""
        try:
            # This task would handle continuous frame capture
            # In a real implementation, it would work with WebRTC streams
            pass
        except Exception as e:
            logger.error(f"Error in frame processor task: {e}", exc_info=True)

    @tasks.loop(seconds=0.1)
    async def audio_player_task(self) -> None:
        """Background task to play TTS audio from the audio queue."""
        try:
            if self.audio_queue.empty():
                return

            # Get audio file from queue (non-blocking)
            try:
                audio_data = self.audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                return

            try:
                # Play audio in all connected voice channels
                played = False
                for guild_id, voice_client in self.voice_clients.items():
                    if voice_client.is_connected() and not voice_client.is_playing():
                        try:
                            await self.audio_player.play_audio(
                                voice_client,
                                audio_data
                            )
                            logger.debug(f"Playing audio in guild {guild_id}")
                            played = True
                        except Exception as e:
                            logger.error(
                                f"Error playing audio in guild {guild_id}: {e}",
                                exc_info=True
                            )

                if not played:
                    logger.warning("Audio not played in any voice channel (no available clients)")
            finally:
                # Always mark task as done, even if playback failed
                self.audio_queue.task_done()

        except Exception as e:
            logger.error(f"Error in audio player task: {e}", exc_info=True)

    @frame_processor_task.before_loop
    async def before_frame_processor(self) -> None:
        """Wait for bot to be ready before starting frame processor."""
        await self.wait_until_ready()

    @audio_player_task.before_loop
    async def before_audio_player(self) -> None:
        """Wait for bot to be ready before starting audio player."""
        await self.wait_until_ready()

    async def close(self) -> None:
        """Clean up resources when shutting down."""
        logger.info("Shutting down AnnouncerBot...")

        # Cancel background tasks
        self.frame_processor_task.cancel()
        self.audio_player_task.cancel()

        # Disconnect from all voice channels
        for guild_id, voice_client in list(self.voice_clients.items()):
            try:
                if voice_client.is_connected():
                    await voice_client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from guild {guild_id}: {e}")

        self.voice_clients.clear()

        await super().close()
        logger.info("AnnouncerBot shutdown complete")


async def run_bot(
    token: str,
    frame_queue: asyncio.Queue,
    audio_queue: asyncio.Queue,
    command_prefix: str = "!",
    frame_rate: float = 1.0
) -> None:
    """Run the Discord bot.

    Args:
        token: Discord bot token
        frame_queue: Queue for captured frames
        audio_queue: Queue for TTS audio files
        command_prefix: Command prefix for bot commands
        frame_rate: Frames per second to capture
    """
    bot = AnnouncerBot(
        command_prefix=command_prefix,
        frame_queue=frame_queue,
        audio_queue=audio_queue,
        frame_rate=frame_rate
    )

    try:
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
    finally:
        await bot.close()
