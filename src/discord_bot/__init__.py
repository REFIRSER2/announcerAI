"""Discord Bot module for LoL Announcer AI.

This module provides Discord bot functionality including:
- Voice channel join/leave commands
- Screen share stream capture
- TTS audio playback
- Frame extraction and processing
"""

from .bot import AnnouncerBot
from .stream_capture import StreamCapture
from .audio_player import AudioPlayer

__all__ = [
    "AnnouncerBot",
    "StreamCapture",
    "AudioPlayer",
]

__version__ = "1.0.0"
