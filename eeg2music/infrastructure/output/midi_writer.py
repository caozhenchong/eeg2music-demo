"""Dependency-free Standard MIDI File writer."""

from __future__ import annotations

import random
import struct
from pathlib import Path

import numpy as np

from ...domain.models import MusicControls


def _variable_length_quantity(value: int) -> bytes:
    value = max(0, int(value))
    output = bytearray([value & 0x7F])
    while value >> 7:
        value >>= 7
        output.insert(0, (value & 0x7F) | 0x80)
    return bytes(output)


def write_demo_midi(
    output_path: Path,
    controls: MusicControls,
    band_relative: dict[str, float],
    seed_text: str = "eeg2music",
) -> None:
    """此处可接入实际算法：替换为生成模型输出的 MIDI token 序列。"""
    ticks_per_quarter = 480
    root_map = {
        "C": 0,
        "C#": 1,
        "D": 2,
        "D#": 3,
        "E": 4,
        "F": 5,
        "F#": 6,
        "G": 7,
        "G#": 8,
        "A": 9,
        "A#": 10,
        "B": 11,
    }
    root = 60 + root_map.get(controls.key_root, 0)
    scale = (
        [0, 2, 4, 5, 7, 9, 11]
        if controls.mode == "major"
        else [0, 2, 3, 5, 7, 8, 10]
    )
    progression = [0, 4, 5, 3] if controls.mode == "major" else [0, 5, 2, 6]
    bar_ticks = ticks_per_quarter * 4

    weighted_power = sum(
        (index + 1) * value for index, value in enumerate(band_relative.values())
    )
    rng = random.Random(sum(map(ord, seed_text)) + int(10000 * weighted_power))
    events: list[tuple[int, int, bytes]] = []

    micros_per_quarter = int(60_000_000 / max(1, controls.tempo_bpm))
    events.append(
        (0, 0, b"\xff\x51\x03" + micros_per_quarter.to_bytes(3, "big"))
    )
    events.append((0, 1, b"\xff\x58\x04\x04\x02\x18\x08"))
    events.append(
        (0, 2, bytes([0xC0, int(np.clip(controls.midi_program, 0, 127))]))
    )

    for bar in range(controls.bars):
        bar_start = bar * bar_ticks
        degree = progression[bar % len(progression)]
        chord_notes = [
            root - 12 + scale[(degree + offset) % 7] for offset in (0, 2, 4)
        ]
        chord_velocity = max(28, controls.velocity - 24)
        for note in chord_notes:
            events.append((bar_start, 10, bytes([0x90, note, chord_velocity])))
            events.append((bar_start + bar_ticks - 20, 5, bytes([0x80, note, 0])))

        step_ticks = ticks_per_quarter // 2
        for step in range(8):
            if step not in (0, 4) and rng.random() > controls.density:
                continue
            note_degree = (degree + rng.choice([0, 1, 2, 4, 6])) % 7
            octave = 12 if controls.density > 0.62 and rng.random() > 0.55 else 0
            note = int(np.clip(root + scale[note_degree] + octave, 36, 96))
            start = bar_start + step * step_ticks
            length = int(step_ticks * (0.72 if controls.density > 0.55 else 0.92))
            velocity = int(np.clip(controls.velocity + rng.randint(-8, 8), 1, 127))
            events.append((start, 20, bytes([0x90, note, velocity])))
            events.append((start + length, 4, bytes([0x80, note, 0])))

    events.sort(key=lambda item: (item[0], item[1]))
    track = bytearray()
    previous_tick = 0
    for tick, _priority, event_data in events:
        track.extend(_variable_length_quantity(tick - previous_tick))
        track.extend(event_data)
        previous_tick = tick
    track.extend(_variable_length_quantity(0))
    track.extend(b"\xff\x2f\x00")

    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, ticks_per_quarter)
    body = b"MTrk" + struct.pack(">I", len(track)) + bytes(track)
    Path(output_path).write_bytes(header + body)
