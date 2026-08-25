"""Composition root: the only place where concrete dependencies are wired."""

from __future__ import annotations

from .application import EEG2MusicApplicationService
from .config import OUTPUT_DIR
from .infrastructure import (
    HeuristicBrainStateDecoder,
    LocalResultPublisher,
    MNEEEGDataSource,
    RuleBasedMusicMapper,
    SciPyEEGAnalyzer,
)


def build_application_service() -> EEG2MusicApplicationService:
    """Create the standalone application graph."""
    return EEG2MusicApplicationService(
        data_source=MNEEEGDataSource(),
        analyzer=SciPyEEGAnalyzer(),
        brain_state_decoder=HeuristicBrainStateDecoder(),
        music_mapper=RuleBasedMusicMapper(),
        result_publisher=LocalResultPublisher(OUTPUT_DIR),
    )
