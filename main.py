#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EEG2Music demo application entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from eeg2music.bootstrap import build_application_service
from eeg2music.config import DEFAULT_DATA_DIR
from eeg2music.ui import EEG2MusicGUI


def run_self_test(data_path: Path, file_path: Path | None, seconds: float) -> int:
    """Process one real file without opening a window."""
    application = build_application_service()
    files = [file_path] if file_path else application.find_files(data_path)
    files = [Path(path) for path in files if path is not None]
    if not files:
        print(f"SELF-TEST FAILED: 未找到 EEG 文件：{data_path}")
        return 2

    print("处理引擎：独立 SciPy 实现")
    result = application.analyze_file(
        files[0], max_duration_sec=seconds, progress=print, publish_outputs=True
    )
    print(json.dumps(result.summary(), ensure_ascii=False, indent=2))
    if not result.midi_path or not Path(result.midi_path).exists():
        print("SELF-TEST FAILED: MIDI 未生成")
        return 3
    print("SELF-TEST PASSED")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EEG2Music Demo GUI")
    parser.add_argument(
        "--self-test", action="store_true", help="不打开 GUI，处理首个文件并退出"
    )
    parser.add_argument(
        "--data", type=Path, default=DEFAULT_DATA_DIR, help="EEG 数据目录"
    )
    parser.add_argument("--file", type=Path, default=None, help="指定单个 EEG 文件")
    parser.add_argument("--seconds", type=float, default=10.0, help="自检分析时长")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_arg_parser().parse_args(list(argv) if argv is not None else None)
    if args.self_test:
        return run_self_test(args.data, args.file, max(4.0, args.seconds))
    app = EEG2MusicGUI(build_application_service())
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
