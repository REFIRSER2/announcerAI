"""
AI Vision Analyzer Module for League of Legends Stream Analysis.

This module provides vision-based analysis of LoL game streams using AI APIs,
event detection, and automatic commentary generation.
"""

from .analyzer import VisionAnalyzer, GameState
from .commentary_generator import CommentaryGenerator, CommentaryPattern
from .event_detector import EventDetector, EventType, GameEvent

__all__ = [
    "VisionAnalyzer",
    "GameState",
    "CommentaryGenerator",
    "CommentaryPattern",
    "EventDetector",
    "EventType",
    "GameEvent",
]

__version__ = "1.0.0"
