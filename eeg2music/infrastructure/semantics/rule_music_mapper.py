"""Explainable placeholder implementation of the MusicMapper port."""

from __future__ import annotations

import numpy as np

from ...domain.models import BrainState, MusicControls


class RuleBasedMusicMapper:
    """Map a brain state to deterministic, interpretable music controls."""

    def map(
        self, brain_state: BrainState, band_relative: dict[str, float]
    ) -> MusicControls:
        """此处可接入实际算法：替换为 Brain-Music Semantic Bridge。"""
        tempo = int(np.clip(round(96 + 32 * brain_state.arousal), 60, 150))
        mode = "major" if brain_state.valence >= 0 else "minor"
        positive_roots = ["C", "G", "D", "A", "E", "F"]
        negative_roots = ["A", "E", "D", "B", "G", "C"]
        alpha = float(band_relative.get("Alpha", 0.0))
        root_index = min(5, int(np.clip(alpha * 8.0, 0, 5)))
        key_root = (
            positive_roots if brain_state.valence >= 0 else negative_roots
        )[root_index]

        if brain_state.arousal > 0.45:
            instrument, midi_program = "Bright Acoustic Piano", 1
        elif brain_state.valence < -0.25:
            instrument, midi_program = "String Ensemble", 48
        else:
            instrument, midi_program = "Electric Piano", 4

        return MusicControls(
            tempo_bpm=tempo,
            key_root=key_root,
            mode=mode,
            instrument=instrument,
            midi_program=midi_program,
            density=float(
                np.clip(0.45 + 0.35 * brain_state.arousal, 0.18, 0.88)
            ),
            velocity=int(
                np.clip(round(70 + 28 * brain_state.arousal), 42, 112)
            ),
        )
