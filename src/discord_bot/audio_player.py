"""Audio player module for playing TTS audio in Discord voice channels.

This module handles:
- Playing TTS-generated audio files in Discord voice channels
- Audio queue management
- FFmpeg-based audio streaming
- Playback control (play, pause, stop)
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, Union, Dict, Any, Callable
from collections import deque

import discord


logger = logging.getLogger(__name__)


class AudioPlayer:
    """Plays TTS audio files in Discord voice channels.

    This class manages audio playback using FFmpeg, including:
    - Playing audio files from disk or bytes
    - Queue management for sequential playback
    - Playback control and status tracking
    - Error handling and recovery

    Attributes:
        ffmpeg_options: Options for FFmpeg audio processing
        playback_queue: Queue of audio files to play
        current_playback: Currently playing audio source
        is_playing: Whether audio is currently playing
    """

    # Default FFmpeg options for audio playback
    DEFAULT_FFMPEG_OPTIONS = {
        'options': '-vn',  # No video
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
    }

    def __init__(
        self,
        ffmpeg_options: Optional[Dict[str, Any]] = None,
        volume: float = 1.0
    ):
        """Initialize the AudioPlayer.

        Args:
            ffmpeg_options: Custom FFmpeg options (uses defaults if None)
            volume: Initial volume level (0.0 to 1.0)
        """
        self.ffmpeg_options = ffmpeg_options or self.DEFAULT_FFMPEG_OPTIONS.copy()
        self.volume = max(0.0, min(1.0, volume))  # Clamp between 0 and 1

        # Playback state
        self.playback_queue: deque = deque()
        self.current_playback: Optional[discord.AudioSource] = None
        self.is_playing = False

        # Callbacks
        self.on_playback_start: Optional[Callable] = None
        self.on_playback_end: Optional[Callable] = None
        self.on_playback_error: Optional[Callable] = None

        logger.info(f"AudioPlayer initialized with volume={volume}")

    async def play_audio(
        self,
        voice_client: discord.VoiceClient,
        audio_data: Union[str, Path, bytes, Dict[str, Any]],
        wait_finish: bool = False
    ) -> bool:
        """Play audio in a Discord voice channel.

        Args:
            voice_client: Discord voice client to play audio through
            audio_data: Audio file path, bytes, or dict with 'path'/'data' key
            wait_finish: Whether to wait for playback to finish

        Returns:
            True if playback started successfully, False otherwise
        """
        try:
            if not voice_client.is_connected():
                logger.error("Voice client is not connected")
                return False

            # Parse audio data
            audio_source = self._create_audio_source(audio_data)
            if audio_source is None:
                logger.error("Failed to create audio source")
                return False

            # Stop current playback if any
            if voice_client.is_playing():
                voice_client.stop()
                await asyncio.sleep(0.1)  # Brief pause

            # Set up playback complete callback
            playback_complete = asyncio.Event()

            def after_playback(error: Optional[Exception]) -> None:
                """Callback after playback completes."""
                self.is_playing = False
                self.current_playback = None
                playback_complete.set()

                if error:
                    logger.error(f"Playback error: {error}")
                    if self.on_playback_error:
                        asyncio.create_task(self._call_callback(
                            self.on_playback_error,
                            error
                        ))
                else:
                    logger.debug("Playback completed successfully")
                    if self.on_playback_end:
                        asyncio.create_task(self._call_callback(
                            self.on_playback_end
                        ))

            # Start playback
            voice_client.play(audio_source, after=after_playback)
            self.is_playing = True
            self.current_playback = audio_source

            logger.info("Audio playback started")

            if self.on_playback_start:
                await self._call_callback(self.on_playback_start)

            # Wait for playback to finish if requested
            if wait_finish:
                await playback_complete.wait()

            return True

        except Exception as e:
            logger.error(f"Error playing audio: {e}", exc_info=True)
            self.is_playing = False
            return False

    def _create_audio_source(
        self,
        audio_data: Union[str, Path, bytes, Dict[str, Any]]
    ) -> Optional[discord.AudioSource]:
        """Create a Discord audio source from audio data.

        Args:
            audio_data: Audio file path, bytes, or dict

        Returns:
            Discord AudioSource or None if creation failed
        """
        try:
            # Handle different input types
            if isinstance(audio_data, dict):
                if 'path' in audio_data:
                    audio_path = audio_data['path']
                elif 'data' in audio_data:
                    # For bytes data, write to temp file
                    return self._create_audio_source_from_bytes(audio_data['data'])
                else:
                    logger.error("Invalid audio data dict")
                    return None
            elif isinstance(audio_data, bytes):
                # Handle bytes directly
                return self._create_audio_source_from_bytes(audio_data)
            else:
                audio_path = audio_data

            # Convert to Path object
            if isinstance(audio_path, str):
                audio_path = Path(audio_path)

            # Check if file exists
            if not audio_path.exists():
                logger.error(f"Audio file not found: {audio_path}")
                return None

            # Create FFmpeg audio source
            audio_source = discord.FFmpegPCMAudio(
                str(audio_path),
                **self.ffmpeg_options
            )

            # Apply volume transformation
            audio_source = discord.PCMVolumeTransformer(
                audio_source,
                volume=self.volume
            )

            return audio_source

        except Exception as e:
            logger.error(f"Error creating audio source: {e}", exc_info=True)
            return None

    def _create_audio_source_from_bytes(self, audio_bytes: bytes) -> Optional[discord.AudioSource]:
        """Create a Discord audio source from bytes data.

        Args:
            audio_bytes: Audio data as bytes (WAV format)

        Returns:
            Discord AudioSource or None if creation failed
        """
        try:
            # Write bytes to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name

            logger.debug(f"Created temporary audio file: {temp_path}")

            # Create FFmpeg audio source
            audio_source = discord.FFmpegPCMAudio(
                temp_path,
                **self.ffmpeg_options
            )

            # Apply volume transformation
            audio_source = discord.PCMVolumeTransformer(
                audio_source,
                volume=self.volume
            )

            # Note: The temporary file is not deleted immediately to allow FFmpeg to read it.
            # The OS will clean it up from /tmp periodically. For production use,
            # consider implementing a cleanup mechanism after playback completes.
            return audio_source

        except Exception as e:
            logger.error(f"Error creating audio source from bytes: {e}", exc_info=True)
            return None

    async def play_from_queue(
        self,
        voice_client: discord.VoiceClient
    ) -> bool:
        """Play the next audio from the queue.

        Args:
            voice_client: Discord voice client

        Returns:
            True if playback started, False if queue is empty or error occurred
        """
        try:
            if not self.playback_queue:
                logger.debug("Playback queue is empty")
                return False

            audio_data = self.playback_queue.popleft()
            return await self.play_audio(voice_client, audio_data)

        except Exception as e:
            logger.error(f"Error playing from queue: {e}", exc_info=True)
            return False

    def enqueue_audio(
        self,
        audio_data: Union[str, Path, bytes, Dict[str, Any]]
    ) -> None:
        """Add audio to the playback queue.

        Args:
            audio_data: Audio file path, bytes, or dict
        """
        self.playback_queue.append(audio_data)
        logger.debug(f"Audio enqueued. Queue size: {len(self.playback_queue)}")

    def stop_playback(self, voice_client: discord.VoiceClient) -> None:
        """Stop current audio playback.

        Args:
            voice_client: Discord voice client
        """
        try:
            if voice_client.is_playing():
                voice_client.stop()
                logger.info("Audio playback stopped")
        except Exception as e:
            logger.error(f"Error stopping playback: {e}", exc_info=True)

    def pause_playback(self, voice_client: discord.VoiceClient) -> None:
        """Pause current audio playback.

        Args:
            voice_client: Discord voice client
        """
        try:
            if voice_client.is_playing() and not voice_client.is_paused():
                voice_client.pause()
                logger.info("Audio playback paused")
        except Exception as e:
            logger.error(f"Error pausing playback: {e}", exc_info=True)

    def resume_playback(self, voice_client: discord.VoiceClient) -> None:
        """Resume paused audio playback.

        Args:
            voice_client: Discord voice client
        """
        try:
            if voice_client.is_paused():
                voice_client.resume()
                logger.info("Audio playback resumed")
        except Exception as e:
            logger.error(f"Error resuming playback: {e}", exc_info=True)

    def set_volume(self, volume: float) -> None:
        """Set the playback volume.

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self.volume = max(0.0, min(1.0, volume))
        logger.info(f"Volume set to {self.volume}")

        # Update current playback volume if applicable
        if self.current_playback and isinstance(
            self.current_playback,
            discord.PCMVolumeTransformer
        ):
            self.current_playback.volume = self.volume

    def get_queue_size(self) -> int:
        """Get the number of items in the playback queue.

        Returns:
            Queue size
        """
        return len(self.playback_queue)

    def clear_queue(self) -> None:
        """Clear all items from the playback queue."""
        self.playback_queue.clear()
        logger.info("Playback queue cleared")

    def get_status(self) -> Dict[str, Any]:
        """Get the current playback status.

        Returns:
            Dictionary with status information
        """
        return {
            "is_playing": self.is_playing,
            "queue_size": len(self.playback_queue),
            "volume": self.volume,
            "has_current_playback": self.current_playback is not None,
        }

    async def _call_callback(
        self,
        callback: Callable,
        *args: Any,
        **kwargs: Any
    ) -> None:
        """Safely call a callback function.

        Args:
            callback: Callback function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in callback: {e}", exc_info=True)


class AudioQueueManager:
    """Manages automatic audio playback from an asyncio queue.

    This class monitors an asyncio queue and automatically plays
    audio as it becomes available.
    """

    def __init__(
        self,
        audio_player: AudioPlayer,
        audio_queue: asyncio.Queue
    ):
        """Initialize the AudioQueueManager.

        Args:
            audio_player: AudioPlayer instance to use for playback
            audio_queue: asyncio Queue containing audio data
        """
        self.audio_player = audio_player
        self.audio_queue = audio_queue
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

        logger.info("AudioQueueManager initialized")

    async def start(self, voice_client: discord.VoiceClient) -> None:
        """Start monitoring the queue and playing audio.

        Args:
            voice_client: Discord voice client to play audio through
        """
        if self.is_running:
            logger.warning("AudioQueueManager already running")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._run(voice_client))
        logger.info("AudioQueueManager started")

    async def stop(self) -> None:
        """Stop the queue manager."""
        self.is_running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("AudioQueueManager stopped")

    async def _run(self, voice_client: discord.VoiceClient) -> None:
        """Main loop for processing audio queue.

        Args:
            voice_client: Discord voice client
        """
        logger.info("AudioQueueManager loop started")

        while self.is_running:
            try:
                # Wait for audio data from queue
                audio_data = await self.audio_queue.get()

                # Play the audio
                await self.audio_player.play_audio(
                    voice_client,
                    audio_data,
                    wait_finish=True
                )

                # Mark task as done
                self.audio_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in AudioQueueManager loop: {e}", exc_info=True)
                await asyncio.sleep(1)  # Brief pause before retrying

        logger.info("AudioQueueManager loop ended")
