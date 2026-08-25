"""Standalone EEG2Music demo package."""

from .config import DEFAULT_DATA_DIR
from .domain import EEGResult, MusicControls

__all__ = ["DEFAULT_DATA_DIR", "EEGResult", "MusicControls"]
