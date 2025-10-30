"""
TTS Client Module

This module provides a client for communicating with the ttsclient server.
It handles REST API requests to generate text-to-speech audio files.
"""

import logging
from typing import Optional, Literal
import aiohttp
from pathlib import Path
import io

# Set up logging
logger = logging.getLogger(__name__)


# Type aliases matching ttsclient API
LanguageType = Literal[
    "all_zh", "en", "all_ja", "all_yue", "all_ko",
    "zh", "ja", "yue", "ko", "auto", "auto_yue"
]

CutMethod = Literal[
    "No slice",
    "Slice once every 4 sentences",
    "Slice per 50 characters",
    "Slice by Chinese punct",
    "Slice by English punct",
    "Slice by every punct"
]


class TTSClientError(Exception):
    """Base exception for TTS Client errors."""
    pass


class TTSServerConnectionError(TTSClientError):
    """Exception raised when cannot connect to TTS server."""
    pass


class TTSGenerationError(TTSClientError):
    """Exception raised when TTS generation fails."""
    pass


class TTSClient:
    """
    Client for communicating with ttsclient server.

    This class handles REST API requests to generate text-to-speech audio.
    It uses aiohttp for asynchronous HTTP communication.

    Attributes:
        base_url (str): Base URL of the TTS server
        timeout (int): Request timeout in seconds
        session (Optional[aiohttp.ClientSession]): Reusable HTTP session
    """

    def __init__(
        self,
        base_url: str = "http://localhost:50021",
        timeout: int = 30
    ):
        """
        Initialize TTS Client.

        Args:
            base_url: Base URL of the TTS server (default: http://localhost:50021)
            timeout: Request timeout in seconds (default: 30)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"TTS Client initialized with base_url: {self.base_url}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """
        Create and initialize the HTTP session.

        This should be called before making any requests.
        """
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.debug("HTTP session created")

    async def close(self) -> None:
        """
        Close the HTTP session.

        This should be called when done with the client to clean up resources.
        """
        if self.session is not None:
            await self.session.close()
            self.session = None
            logger.debug("HTTP session closed")

    async def health_check(self) -> bool:
        """
        Check if the TTS server is available.

        Returns:
            bool: True if server is accessible, False otherwise
        """
        try:
            if self.session is None:
                await self.connect()

            url = f"{self.base_url}/api/configuration-manager/configuration"
            async with self.session.get(url) as response:
                is_healthy = response.status == 200
                logger.debug(f"Health check result: {is_healthy}")
                return is_healthy
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    async def generate_voice(
        self,
        text: str,
        voice_character_slot_index: int = 0,
        reference_voice_slot_index: int = 0,
        language: LanguageType = "auto",
        speed: float = 1.0,
        cut_method: CutMethod = "No slice",
        sample_steps: Optional[int] = None,
        phone_symbols: Optional[list[str]] = None
    ) -> bytes:
        """
        Generate speech audio from text.

        Args:
            text: The text to convert to speech
            voice_character_slot_index: Index of the voice character slot (default: 0)
            reference_voice_slot_index: Index of the reference voice slot (default: 0)
            language: Language type for the text (default: "auto")
            speed: Speech speed multiplier (default: 1.0)
            cut_method: Method for slicing long text (default: "No slice")
            sample_steps: Optional sampling steps for generation
            phone_symbols: Optional phone symbols for advanced control

        Returns:
            bytes: WAV audio file data

        Raises:
            TTSServerConnectionError: If cannot connect to TTS server
            TTSGenerationError: If TTS generation fails
        """
        if self.session is None:
            await self.connect()

        # Prepare request payload
        payload = {
            "voice_character_slot_index": voice_character_slot_index,
            "reference_voice_slot_index": reference_voice_slot_index,
            "text": text,
            "language": language,
            "speed": speed,
            "cutMethod": cut_method,
        }

        # Add optional parameters
        if sample_steps is not None:
            payload["sample_steps"] = sample_steps
        if phone_symbols is not None:
            payload["phone_symbols"] = phone_symbols

        url = f"{self.base_url}/api/tts-manager/operation/generateVoice"

        logger.info(f"Generating voice for text: '{text[:50]}...' (length: {len(text)})")
        logger.debug(f"Request payload: {payload}")

        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    logger.info(f"Successfully generated audio ({len(audio_data)} bytes)")
                    return audio_data
                else:
                    error_text = await response.text()
                    logger.error(f"TTS generation failed: {response.status} - {error_text}")
                    raise TTSGenerationError(
                        f"TTS generation failed with status {response.status}: {error_text}"
                    )
        except aiohttp.ClientError as e:
            logger.error(f"Connection error: {e}")
            raise TTSServerConnectionError(f"Cannot connect to TTS server: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise TTSGenerationError(f"Unexpected error during TTS generation: {e}")

    async def save_voice_to_file(
        self,
        text: str,
        output_path: Path,
        voice_character_slot_index: int = 0,
        reference_voice_slot_index: int = 0,
        language: LanguageType = "auto",
        speed: float = 1.0,
        cut_method: CutMethod = "No slice",
        sample_steps: Optional[int] = None
    ) -> Path:
        """
        Generate speech audio and save it to a file.

        Args:
            text: The text to convert to speech
            output_path: Path where the audio file will be saved
            voice_character_slot_index: Index of the voice character slot (default: 0)
            reference_voice_slot_index: Index of the reference voice slot (default: 0)
            language: Language type for the text (default: "auto")
            speed: Speech speed multiplier (default: 1.0)
            cut_method: Method for slicing long text (default: "No slice")
            sample_steps: Optional sampling steps for generation

        Returns:
            Path: Path to the saved audio file

        Raises:
            TTSServerConnectionError: If cannot connect to TTS server
            TTSGenerationError: If TTS generation fails
        """
        audio_data = await self.generate_voice(
            text=text,
            voice_character_slot_index=voice_character_slot_index,
            reference_voice_slot_index=reference_voice_slot_index,
            language=language,
            speed=speed,
            cut_method=cut_method,
            sample_steps=sample_steps
        )

        # Save to file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(audio_data)

        logger.info(f"Audio saved to: {output_path}")
        return output_path


# Example usage
async def main():
    """Example usage of TTSClient."""
    async with TTSClient() as client:
        # Check if server is available
        if not await client.health_check():
            logger.error("TTS server is not available")
            return

        # Generate voice
        text = "Hello, this is a test message."
        audio_data = await client.generate_voice(
            text=text,
            language="en",
            speed=1.0
        )

        # Save to file
        output_path = Path("output.wav")
        await client.save_voice_to_file(
            text=text,
            output_path=output_path
        )


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
