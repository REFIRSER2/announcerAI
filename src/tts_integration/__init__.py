"""
TTS Integration Module

This module provides integration with the ttsclient TTS server.
It includes a client for making TTS requests and a manager for
handling request queues asynchronously.

Main Components:
    - TTSClient: Client for communicating with TTS server
    - TTSManager: Manager for handling TTS request queues
    - TTSRequest: Data structure for TTS requests
    - TTSRequestStatus: Enum for request status

Example usage:
    ```python
    from tts_integration import TTSClient, TTSManager

    # Using TTSClient directly
    async with TTSClient() as client:
        audio_data = await client.generate_voice("Hello world")

    # Using TTSManager for queue-based processing
    manager = TTSManager(audio_callback=my_audio_handler)
    await manager.start()
    request_id = await manager.add_request("Hello world")
    # ... process requests ...
    await manager.stop()
    ```
"""

from .tts_client import (
    TTSClient,
    TTSClientError,
    TTSServerConnectionError,
    TTSGenerationError,
    LanguageType,
    CutMethod,
)

from .tts_manager import (
    TTSManager,
    TTSRequest,
    TTSRequestStatus,
)

__all__ = [
    # Client classes
    "TTSClient",
    "TTSClientError",
    "TTSServerConnectionError",
    "TTSGenerationError",
    # Manager classes
    "TTSManager",
    "TTSRequest",
    "TTSRequestStatus",
    # Type aliases
    "LanguageType",
    "CutMethod",
]

__version__ = "1.0.0"
