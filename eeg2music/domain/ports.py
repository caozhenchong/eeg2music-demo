"""Protocols owned by the domain/application side of the architecture."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol

from .models import BrainState, EEGAnalysis, EEGRecording, EEGResult, MusicControls


ProgressCallback = Callable[[str], None]


class EEGDataSource(Protocol):
    """Port for discovering and reading EEG recordings."""

    def find_files(self, data_dir: Path) -> list[Path]: ...

    def inspect(self, file_path: Path) -> dict: ...

    def load_window(
        self,
        file_path: Path,
        max_duration_sec: float,
        progress: ProgressCallback,
    ) -> EEGRecording: ...


class EEGAnalyzer(Protocol):
    """Port for local preprocessing and signal-level feature extraction."""

    def analyze(
        self, recording: EEGRecording, progress: ProgressCallback
    ) -> EEGAnalysis: ...


class BrainStateDecoder(Protocol):
    """Port for converting EEG features into the semantic V-A space."""

    def decode(self, recording: EEGRecording, analysis: EEGAnalysis) -> BrainState: ...


class MusicMapper(Protocol):
    """Port for producing interpretable music conditions."""

    def map(
        self, brain_state: BrainState, band_relative: dict[str, float]
    ) -> MusicControls: ...


class ResultPublisher(Protocol):
    """Port for writing result artifacts without coupling the use case to files."""

    def publish(
        self,
        result: EEGResult,
        source_path: Path,
        progress: ProgressCallback,
    ) -> None: ...
