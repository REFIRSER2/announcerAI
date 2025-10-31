"""Stream capture module for extracting frames from Discord screen shares.

This module handles capturing frames from Discord screen share streams
and processing them for AI vision analysis.
"""

import asyncio
import logging
from typing import Optional, Union, Tuple
from io import BytesIO

import cv2
import numpy as np
from PIL import Image


logger = logging.getLogger(__name__)


class StreamCapture:
    """Captures and processes frames from Discord screen share streams.

    This class handles:
    - Frame extraction from video streams
    - Frame rate control
    - Image format conversion (numpy array / PIL Image)
    - Frame preprocessing and optimization

    Attributes:
        frame_rate: Number of frames to capture per second
        target_size: Optional target size for resizing frames (width, height)
        last_capture_time: Timestamp of last captured frame
    """

    def __init__(
        self,
        frame_rate: float = 1.0,
        target_size: Optional[Tuple[int, int]] = None,
        quality: int = 95
    ):
        """Initialize the StreamCapture.

        Args:
            frame_rate: Frames per second to capture (default: 1.0)
            target_size: Optional target size for resizing frames (width, height)
            quality: JPEG quality for frame compression (0-100, default: 95)
        """
        self.frame_rate = frame_rate
        self.target_size = target_size
        self.quality = quality
        self.last_capture_time = 0.0

        logger.info(
            f"StreamCapture initialized with frame_rate={frame_rate}, "
            f"target_size={target_size}, quality={quality}"
        )

    @property
    def frame_interval(self) -> float:
        """Get the interval between frames in seconds."""
        return 1.0 / self.frame_rate if self.frame_rate > 0 else 1.0

    async def capture_frame(
        self,
        stream_data: Union[bytes, np.ndarray],
        output_format: str = "pil"
    ) -> Optional[Union[Image.Image, np.ndarray]]:
        """Capture and process a single frame from the stream.

        Args:
            stream_data: Raw stream data (bytes or numpy array)
            output_format: Output format - "pil" for PIL Image or "numpy" for ndarray

        Returns:
            Processed frame as PIL Image or numpy array, or None if capture failed

        Raises:
            ValueError: If output_format is invalid
        """
        try:
            # Check if enough time has passed since last capture
            current_time = asyncio.get_event_loop().time()
            if current_time - self.last_capture_time < self.frame_interval:
                return None

            self.last_capture_time = current_time

            # Convert stream data to numpy array
            frame = self._decode_frame(stream_data)
            if frame is None:
                logger.warning("Failed to decode frame")
                return None

            # Preprocess frame
            frame = self._preprocess_frame(frame)

            # Convert to requested format
            if output_format == "pil":
                return self._to_pil_image(frame)
            elif output_format == "numpy":
                return frame
            else:
                raise ValueError(f"Invalid output_format: {output_format}")

        except Exception as e:
            logger.error(f"Error capturing frame: {e}", exc_info=True)
            return None

    def _decode_frame(self, stream_data: Union[bytes, np.ndarray]) -> Optional[np.ndarray]:
        """Decode frame data into a numpy array.

        Args:
            stream_data: Raw stream data

        Returns:
            Decoded frame as numpy array, or None if decoding failed
        """
        try:
            if isinstance(stream_data, np.ndarray):
                return stream_data

            elif isinstance(stream_data, bytes):
                # Decode bytes using OpenCV
                nparr = np.frombuffer(stream_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                return frame

            else:
                logger.error(f"Unsupported stream data type: {type(stream_data)}")
                return None

        except Exception as e:
            logger.error(f"Error decoding frame: {e}", exc_info=True)
            return None

    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """Preprocess frame (resize, enhance, etc.).

        Args:
            frame: Input frame as numpy array

        Returns:
            Preprocessed frame
        """
        try:
            # Resize if target size is specified
            if self.target_size is not None:
                frame = cv2.resize(
                    frame,
                    self.target_size,
                    interpolation=cv2.INTER_AREA
                )

            # Convert BGR to RGB (OpenCV uses BGR by default)
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            return frame

        except Exception as e:
            logger.error(f"Error preprocessing frame: {e}", exc_info=True)
            return frame

    def _to_pil_image(self, frame: np.ndarray) -> Image.Image:
        """Convert numpy array to PIL Image.

        Args:
            frame: Frame as numpy array

        Returns:
            Frame as PIL Image
        """
        return Image.fromarray(frame)

    async def capture_from_video_file(
        self,
        video_path: str,
        output_format: str = "pil"
    ) -> Optional[Union[Image.Image, np.ndarray]]:
        """Capture a frame from a video file (for testing).

        Args:
            video_path: Path to video file
            output_format: Output format - "pil" or "numpy"

        Returns:
            Captured frame or None if failed
        """
        try:
            # Open video file
            cap = cv2.VideoCapture(video_path)

            if not cap.isOpened():
                logger.error(f"Failed to open video file: {video_path}")
                return None

            # Read frame
            ret, frame = cap.read()
            cap.release()

            if not ret:
                logger.error("Failed to read frame from video")
                return None

            # Process frame
            return await self.capture_frame(frame, output_format)

        except Exception as e:
            logger.error(f"Error capturing from video file: {e}", exc_info=True)
            return None

    async def capture_from_webcam(
        self,
        camera_index: int = 0,
        output_format: str = "pil"
    ) -> Optional[Union[Image.Image, np.ndarray]]:
        """Capture a frame from webcam (for testing).

        Args:
            camera_index: Camera device index (default: 0)
            output_format: Output format - "pil" or "numpy"

        Returns:
            Captured frame or None if failed
        """
        try:
            # Open webcam
            cap = cv2.VideoCapture(camera_index)

            if not cap.isOpened():
                logger.error(f"Failed to open camera {camera_index}")
                return None

            # Read frame
            ret, frame = cap.read()
            cap.release()

            if not ret:
                logger.error("Failed to read frame from camera")
                return None

            # Process frame
            return await self.capture_frame(frame, output_format)

        except Exception as e:
            logger.error(f"Error capturing from webcam: {e}", exc_info=True)
            return None

    def encode_frame(
        self,
        frame: Union[Image.Image, np.ndarray],
        format: str = "JPEG"
    ) -> Optional[bytes]:
        """Encode frame to bytes for transmission.

        Args:
            frame: Frame as PIL Image or numpy array
            format: Image format (JPEG, PNG, etc.)

        Returns:
            Encoded frame as bytes or None if encoding failed
        """
        try:
            # Convert to PIL Image if needed
            if isinstance(frame, np.ndarray):
                frame = self._to_pil_image(frame)

            # Encode to bytes
            buffer = BytesIO()
            frame.save(buffer, format=format, quality=self.quality)
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Error encoding frame: {e}", exc_info=True)
            return None

    def decode_frame_bytes(
        self,
        frame_bytes: bytes,
        output_format: str = "pil"
    ) -> Optional[Union[Image.Image, np.ndarray]]:
        """Decode frame from bytes.

        Args:
            frame_bytes: Frame data as bytes
            output_format: Output format - "pil" or "numpy"

        Returns:
            Decoded frame or None if decoding failed
        """
        try:
            # Decode to PIL Image
            image = Image.open(BytesIO(frame_bytes))

            if output_format == "pil":
                return image
            elif output_format == "numpy":
                return np.array(image)
            else:
                raise ValueError(f"Invalid output_format: {output_format}")

        except Exception as e:
            logger.error(f"Error decoding frame bytes: {e}", exc_info=True)
            return None

    def get_frame_info(self, frame: Union[Image.Image, np.ndarray]) -> dict:
        """Get information about a frame.

        Args:
            frame: Frame as PIL Image or numpy array

        Returns:
            Dictionary with frame information
        """
        try:
            if isinstance(frame, Image.Image):
                return {
                    "width": frame.width,
                    "height": frame.height,
                    "mode": frame.mode,
                    "format": frame.format,
                }
            elif isinstance(frame, np.ndarray):
                return {
                    "shape": frame.shape,
                    "dtype": str(frame.dtype),
                    "size_bytes": frame.nbytes,
                }
            else:
                return {"error": "Unknown frame type"}

        except Exception as e:
            logger.error(f"Error getting frame info: {e}", exc_info=True)
            return {"error": str(e)}


class FrameBuffer:
    """Buffer for storing recent frames with automatic cleanup.

    Useful for maintaining a sliding window of recent frames.
    """

    def __init__(self, max_size: int = 10):
        """Initialize the frame buffer.

        Args:
            max_size: Maximum number of frames to store
        """
        self.max_size = max_size
        self.frames: list = []
        self.timestamps: list = []

        logger.debug(f"FrameBuffer initialized with max_size={max_size}")

    def add_frame(
        self,
        frame: Union[Image.Image, np.ndarray],
        timestamp: Optional[float] = None
    ) -> None:
        """Add a frame to the buffer.

        Args:
            frame: Frame to add
            timestamp: Optional timestamp for the frame
        """
        if timestamp is None:
            try:
                timestamp = asyncio.get_event_loop().time()
            except RuntimeError:
                # No event loop running, use system time
                import time
                timestamp = time.time()

        self.frames.append(frame)
        self.timestamps.append(timestamp)

        # Remove oldest frame if buffer is full
        if len(self.frames) > self.max_size:
            self.frames.pop(0)
            self.timestamps.pop(0)

    def get_latest_frame(self) -> Optional[Union[Image.Image, np.ndarray]]:
        """Get the most recent frame.

        Returns:
            Latest frame or None if buffer is empty
        """
        return self.frames[-1] if self.frames else None

    def get_all_frames(self) -> list:
        """Get all frames in the buffer.

        Returns:
            List of frames
        """
        return self.frames.copy()

    def clear(self) -> None:
        """Clear all frames from the buffer."""
        self.frames.clear()
        self.timestamps.clear()

    def __len__(self) -> int:
        """Get the number of frames in the buffer."""
        return len(self.frames)
