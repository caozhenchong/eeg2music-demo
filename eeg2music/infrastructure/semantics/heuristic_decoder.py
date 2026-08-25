"""Explainable placeholder for EEG-to-Valence/Arousal decoding."""

from __future__ import annotations

import math

import numpy as np

from ...domain.models import BrainState, EEGAnalysis, EEGRecording


class HeuristicBrainStateDecoder:
    """Produce a deterministic V-A point until a trained decoder is available."""

    def decode(self, recording: EEGRecording, analysis: EEGAnalysis) -> BrainState:
        """此处可接入实际算法：替换为训练后的连续 V-A 推理服务。"""
        name_to_index = {
            name.strip().lower(): index for index, name in enumerate(recording.channels)
        }
        alpha_values = analysis.channel_band_absolute["Alpha"]
        if "f3" in name_to_index and "f4" in name_to_index:
            left = float(alpha_values[name_to_index["f3"]])
            right = float(alpha_values[name_to_index["f4"]])
            asymmetry = math.log(max(right, 1e-12)) - math.log(max(left, 1e-12))
            valence = math.tanh(0.75 * asymmetry)
            source = "F3/F4 frontal alpha asymmetry (demo)"
        else:
            valence = math.tanh(
                2.5
                * (
                    analysis.band_relative.get("Alpha", 0.0)
                    - analysis.band_relative.get("Theta", 0.0)
                )
            )
            source = "alpha-theta fallback (demo)"

        high_frequency = analysis.band_relative.get(
            "Beta", 0.0
        ) + analysis.band_relative.get("Gamma", 0.0)
        low_frequency = analysis.band_relative.get(
            "Alpha", 0.0
        ) + analysis.band_relative.get("Theta", 0.0)
        arousal = math.tanh(
            1.1 * math.log((high_frequency + 1e-8) / (low_frequency + 1e-8))
        )
        valence = float(np.clip(valence, -1.0, 1.0))
        arousal = float(np.clip(arousal, -1.0, 1.0))

        if valence >= 0 and arousal >= 0:
            label = "积极 / 高唤醒"
        elif valence >= 0 and arousal < 0:
            label = "平静 / 积极"
        elif valence < 0 and arousal >= 0:
            label = "紧张 / 高唤醒"
        else:
            label = "低落 / 低唤醒"
        return BrainState(
            valence=valence,
            arousal=arousal,
            label=label,
            source=source,
        )
