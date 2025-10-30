"""
TTS Manager Module

This module manages TTS request queues and processes text-to-speech generation
requests asynchronously. It handles multiple requests sequentially and forwards
generated audio to an audio queue.
"""

import logging
import asyncio
from typing import Optional, Callable, Awaitable
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .tts_client import TTSClient, LanguageType, CutMethod, TTSClientError

# Set up logging
logger = logging.getLogger(__name__)


class TTSRequestStatus(Enum):
    """Status of a TTS request."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TTSRequest:
    """
    Represents a TTS generation request.

    Attributes:
        id: Unique identifier for the request
        text: Text to convert to speech
        voice_character_slot_index: Index of the voice character slot
        reference_voice_slot_index: Index of the reference voice slot
        language: Language type for the text
        speed: Speech speed multiplier
        cut_method: Method for slicing long text
        sample_steps: Optional sampling steps
        status: Current status of the request
        created_at: Timestamp when request was created
        completed_at: Timestamp when request was completed
        error: Error message if request failed
        audio_data: Generated audio data (bytes)
    """
    id: str
    text: str
    voice_character_slot_index: int = 0
    reference_voice_slot_index: int = 0
    language: LanguageType = "auto"
    speed: float = 1.0
    cut_method: CutMethod = "No slice"
    sample_steps: Optional[int] = None
    status: TTSRequestStatus = TTSRequestStatus.PENDING
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    audio_data: Optional[bytes] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class TTSManager:
    """
    Manages TTS request queues and processes requests asynchronously.

    This class handles multiple TTS requests sequentially, generates audio,
    and forwards the results to a callback function (e.g., audio queue).

    Attributes:
        tts_client (TTSClient): TTS client for generating audio
        request_queue (asyncio.Queue): Queue for pending TTS requests
        is_running (bool): Whether the manager is actively processing
        audio_callback: Callback function for handling generated audio
        max_retries (int): Maximum number of retries for failed requests
        worker_task: Background task processing the queue
    """

    def __init__(
        self,
        tts_server_url: str = "http://localhost:50021",
        timeout: int = 30,
        audio_callback: Optional[Callable[[bytes, TTSRequest], Awaitable[None]]] = None,
        max_retries: int = 3,
        default_language: LanguageType = "ko",
        default_speed: float = 1.0,
        voice_character_slot_index: int = 0
    ):
        """
        Initialize TTS Manager.

        Args:
            tts_server_url: Base URL of the TTS server
            timeout: Request timeout in seconds
            audio_callback: Async callback function to handle generated audio
            max_retries: Maximum number of retries for failed requests
            default_language: Default language for TTS generation
            default_speed: Default speech speed multiplier
            voice_character_slot_index: Default voice character slot index
        """
        self.tts_client = TTSClient(base_url=tts_server_url, timeout=timeout)
        self.request_queue: asyncio.Queue[TTSRequest] = asyncio.Queue()
        self.is_running = False
        self.audio_callback = audio_callback
        self.max_retries = max_retries
        self.default_language = default_language
        self.default_speed = default_speed
        self.default_voice_character_slot_index = voice_character_slot_index
        self.worker_task: Optional[asyncio.Task] = None
        self._request_counter = 0
        self._active_requests: dict[str, TTSRequest] = {}
        logger.info("TTS Manager initialized")

    async def start(self) -> None:
        """
        Start the TTS manager.

        This starts the background worker that processes requests from the queue.
        """
        if self.is_running:
            logger.warning("TTS Manager is already running")
            return

        await self.tts_client.connect()

        # Check server health
        if not await self.tts_client.health_check():
            logger.warning("TTS server health check failed, but starting anyway")

        self.is_running = True
        self.worker_task = asyncio.create_task(self._process_queue())
        logger.info("TTS Manager started")

    async def stop(self) -> None:
        """
        Stop the TTS manager.

        This stops the background worker and cleans up resources.
        """
        if not self.is_running:
            logger.warning("TTS Manager is not running")
            return

        self.is_running = False

        # Cancel worker task
        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        # Close TTS client
        await self.tts_client.close()

        logger.info("TTS Manager stopped")

    async def add_request(
        self,
        text: str,
        voice_character_slot_index: Optional[int] = None,
        reference_voice_slot_index: int = 0,
        language: Optional[LanguageType] = None,
        speed: Optional[float] = None,
        cut_method: CutMethod = "No slice",
        sample_steps: Optional[int] = None,
        priority: int = 5
    ) -> str:
        """
        Add a TTS request to the queue.

        Args:
            text: Text to convert to speech
            voice_character_slot_index: Index of the voice character slot (uses default if None)
            reference_voice_slot_index: Index of the reference voice slot
            language: Language type for the text (uses default if None)
            speed: Speech speed multiplier (uses default if None)
            cut_method: Method for slicing long text
            sample_steps: Optional sampling steps
            priority: Priority of the request (currently unused, for future implementation)

        Returns:
            str: Request ID that can be used to track the request
        """
        if not self.is_running:
            raise RuntimeError("TTS Manager is not running. Call start() first.")

        # Use default values if not specified
        if voice_character_slot_index is None:
            voice_character_slot_index = self.default_voice_character_slot_index
        if language is None:
            language = self.default_language
        if speed is None:
            speed = self.default_speed

        # Generate unique request ID
        self._request_counter += 1
        request_id = f"tts_{self._request_counter}_{datetime.now().timestamp()}"

        # Create request
        request = TTSRequest(
            id=request_id,
            text=text,
            voice_character_slot_index=voice_character_slot_index,
            reference_voice_slot_index=reference_voice_slot_index,
            language=language,
            speed=speed,
            cut_method=cut_method,
            sample_steps=sample_steps
        )

        # Add to queue and tracking
        await self.request_queue.put(request)
        self._active_requests[request_id] = request

        logger.info(f"Added TTS request {request_id} to queue (queue size: {self.request_queue.qsize()})")
        return request_id

    async def get_request_status(self, request_id: str) -> Optional[TTSRequest]:
        """
        Get the status of a TTS request.

        Args:
            request_id: ID of the request

        Returns:
            TTSRequest: The request object, or None if not found
        """
        return self._active_requests.get(request_id)

    async def cancel_request(self, request_id: str) -> bool:
        """
        Cancel a pending TTS request.

        Args:
            request_id: ID of the request to cancel

        Returns:
            bool: True if request was cancelled, False if not found or already processing
        """
        request = self._active_requests.get(request_id)
        if request is None:
            logger.warning(f"Request {request_id} not found")
            return False

        if request.status == TTSRequestStatus.PENDING:
            request.status = TTSRequestStatus.CANCELLED
            logger.info(f"Cancelled request {request_id}")
            return True
        else:
            logger.warning(f"Cannot cancel request {request_id} with status {request.status}")
            return False

    def get_queue_size(self) -> int:
        """
        Get the current size of the request queue.

        Returns:
            int: Number of pending requests in the queue
        """
        return self.request_queue.qsize()

    async def _process_queue(self) -> None:
        """
        Background worker that processes requests from the queue.

        This method runs continuously while the manager is active,
        pulling requests from the queue and processing them sequentially.
        """
        logger.info("Queue processor started")

        while self.is_running:
            try:
                # Get next request from queue (with timeout to allow checking is_running)
                try:
                    request = await asyncio.wait_for(
                        self.request_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Check if request was cancelled
                if request.status == TTSRequestStatus.CANCELLED:
                    logger.info(f"Skipping cancelled request {request.id}")
                    self.request_queue.task_done()
                    continue

                # Process the request
                await self._process_request(request)
                self.request_queue.task_done()

            except asyncio.CancelledError:
                logger.info("Queue processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in queue processor: {e}", exc_info=True)
                await asyncio.sleep(1)  # Brief pause before continuing

        logger.info("Queue processor stopped")

    async def _process_request(self, request: TTSRequest) -> None:
        """
        Process a single TTS request.

        Args:
            request: The TTS request to process
        """
        logger.info(f"Processing request {request.id}: '{request.text[:50]}...'")
        request.status = TTSRequestStatus.PROCESSING

        retries = 0
        while retries <= self.max_retries:
            try:
                # Generate audio
                audio_data = await self.tts_client.generate_voice(
                    text=request.text,
                    voice_character_slot_index=request.voice_character_slot_index,
                    reference_voice_slot_index=request.reference_voice_slot_index,
                    language=request.language,
                    speed=request.speed,
                    cut_method=request.cut_method,
                    sample_steps=request.sample_steps
                )

                # Update request
                request.audio_data = audio_data
                request.status = TTSRequestStatus.COMPLETED
                request.completed_at = datetime.now()

                logger.info(f"Successfully processed request {request.id}")

                # Call audio callback if provided
                if self.audio_callback:
                    try:
                        await self.audio_callback(audio_data, request)
                    except Exception as e:
                        logger.error(f"Error in audio callback: {e}", exc_info=True)

                break  # Success, exit retry loop

            except TTSClientError as e:
                retries += 1
                logger.warning(f"Request {request.id} failed (attempt {retries}/{self.max_retries}): {e}")

                if retries > self.max_retries:
                    request.status = TTSRequestStatus.FAILED
                    request.error = str(e)
                    request.completed_at = datetime.now()
                    logger.error(f"Request {request.id} failed after {self.max_retries} retries")
                else:
                    # Wait before retrying (exponential backoff)
                    await asyncio.sleep(2 ** retries)

            except Exception as e:
                logger.error(f"Unexpected error processing request {request.id}: {e}", exc_info=True)
                request.status = TTSRequestStatus.FAILED
                request.error = str(e)
                request.completed_at = datetime.now()
                break

    async def clear_completed_requests(self, keep_recent: int = 10) -> int:
        """
        Clear old completed/failed requests from tracking.

        Args:
            keep_recent: Number of recent requests to keep

        Returns:
            int: Number of requests cleared
        """
        completed_requests = [
            req for req in self._active_requests.values()
            if req.status in (TTSRequestStatus.COMPLETED, TTSRequestStatus.FAILED, TTSRequestStatus.CANCELLED)
        ]

        # Sort by completion time
        completed_requests.sort(key=lambda r: r.completed_at or r.created_at, reverse=True)

        # Remove old requests
        to_remove = completed_requests[keep_recent:]
        for request in to_remove:
            del self._active_requests[request.id]

        if to_remove:
            logger.info(f"Cleared {len(to_remove)} old requests")

        return len(to_remove)


# Example usage
async def audio_handler(audio_data: bytes, request: TTSRequest) -> None:
    """Example audio callback handler."""
    logger.info(f"Received audio for request {request.id}: {len(audio_data)} bytes")
    # Here you would typically add the audio to a playback queue


async def main():
    """Example usage of TTSManager."""
    # Create manager with audio callback
    manager = TTSManager(
        tts_server_url="http://localhost:50021",
        audio_callback=audio_handler
    )

    try:
        # Start the manager
        await manager.start()

        # Add some requests
        request_id_1 = await manager.add_request(
            text="Hello, this is the first message.",
            language="en"
        )

        request_id_2 = await manager.add_request(
            text="This is the second message.",
            language="en",
            speed=1.2
        )

        # Wait for processing
        await asyncio.sleep(2)

        # Check status
        status_1 = await manager.get_request_status(request_id_1)
        if status_1:
            logger.info(f"Request 1 status: {status_1.status}")

        # Wait for all requests to complete
        await asyncio.sleep(10)

    finally:
        # Stop the manager
        await manager.stop()


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
