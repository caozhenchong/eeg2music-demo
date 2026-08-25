"""Local filesystem implementation of the ResultPublisher port."""

from __future__ import annotations

import json
from pathlib import Path

from ...domain.models import EEGResult
from ...domain.ports import ProgressCallback
from .midi_writer import write_demo_midi


class LocalResultPublisher:
    """Publish one MIDI file and one JSON summary into a configured directory."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)

    def publish(
        self,
        result: EEGResult,
        source_path: Path,
        progress: ProgressCallback,
    ) -> None:
        progress("生成演示 MIDI 与 JSON 结果……")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        midi_path = self.output_dir / f"{source_path.stem}_eeg2music_demo.mid"
        json_path = self.output_dir / f"{source_path.stem}_eeg2music_result.json"
        write_demo_midi(
            midi_path, result.music, result.band_relative, source_path.stem
        )
        result.midi_path = str(midi_path)
        result.json_path = str(json_path)
        json_path.write_text(
            json.dumps(result.summary(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
