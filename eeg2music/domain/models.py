"""Domain entities passed between application boundaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np


@dataclass(slots=True)
class EEGRecording:
    """A bounded EEG window loaded in microvolts."""

    source_path: Path
    data_uv: np.ndarray
    sample_rate: float
    channels: list[str]
    total_duration_sec: float

    @property
    def analyzed_duration_sec(self) -> float:
        return float(len(self.data_uv) / self.sample_rate)


@dataclass(slots=True)
class EEGAnalysis:
    """Signal-level analysis before semantic brain-state decoding."""

    clean_data: np.ndarray
    bad_channel_mask: np.ndarray
    quality_score: float
    band_relative: dict[str, float]
    band_absolute: dict[str, float]
    channel_band_absolute: dict[str, np.ndarray]
    individual_alpha_peak_hz: float | None
    processing_info: dict
    preview_time: np.ndarray
    preview_raw: np.ndarray
    preview_clean: np.ndarray
    preview_channels: list[str]
    freqs: np.ndarray
    mean_psd: np.ndarray


@dataclass(slots=True, frozen=True)
class BrainState:
    """Low-dimensional semantic state used to condition music."""

    valence: float
    arousal: float
    label: str
    source: str


@dataclass(slots=True, frozen=True)
class MusicControls:
    """Interpretable conditions sent to a music renderer."""

    tempo_bpm: int
    key_root: str
    mode: str
    instrument: str
    midi_program: int
    density: float
    velocity: int
    bars: int = 4

    @property
    def display_key(self) -> str:
        return f"{self.key_root} {self.mode}"


@dataclass(slots=True)
class EEGResult:
    """Final use-case response consumed by the GUI and local publisher."""

    file_path: str
    sample_rate: float
    channels: list[str]
    duration_sec: float
    analyzed_duration_sec: float
    bad_channels: list[str]
    quality_score: float
    valence: float
    arousal: float
    emotion_label: str
    valence_source: str
    band_relative: dict[str, float]
    band_absolute: dict[str, float]
    individual_alpha_peak_hz: float | None
    processing_info: dict
    music: MusicControls
    preview_time: np.ndarray = field(repr=False)
    preview_raw: np.ndarray = field(repr=False)
    preview_clean: np.ndarray = field(repr=False)
    preview_channels: list[str] = field(repr=False)
    freqs: np.ndarray = field(repr=False)
    mean_psd: np.ndarray = field(repr=False)
    midi_path: str | None = None
    json_path: str | None = None

    def summary(self) -> dict:
        """Return a JSON-safe representation without large plot arrays."""
        return {
            "file_path": self.file_path,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "duration_sec": self.duration_sec,
            "analyzed_duration_sec": self.analyzed_duration_sec,
            "bad_channels": self.bad_channels,
            "quality_score": self.quality_score,
            "valence": self.valence,
            "arousal": self.arousal,
            "emotion_label": self.emotion_label,
            "valence_source": self.valence_source,
            "band_relative": self.band_relative,
            "band_absolute": self.band_absolute,
            "individual_alpha_peak_hz": self.individual_alpha_peak_hz,
            "processing_info": self.processing_info,
            "music": asdict(self.music),
            "midi_path": self.midi_path,
            "json_path": self.json_path,
            "algorithm_note": "V-A 与音乐生成当前为演示映射；此处可接入实际算法。",
        }
