"""MNE implementation of the EEGDataSource port."""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np

from ...config import SUPPORTED_EXTENSIONS
from ...domain.models import EEGRecording
from ...domain.ports import ProgressCallback


class MNEEEGDataSource:
    """Discover and read CNT/EDF/BDF/FIF files as microvolt recordings."""

    @staticmethod
    def find_files(data_dir: Path) -> list[Path]:
        data_dir = Path(data_dir)
        if data_dir.is_file() and data_dir.suffix.lower() in SUPPORTED_EXTENSIONS:
            return [data_dir]
        if not data_dir.exists():
            return []
        return sorted(
            (
                path
                for path in data_dir.rglob("*")
                if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
            ),
            key=lambda path: path.name.lower(),
        )

    @staticmethod
    def _open_raw(file_path: Path, preload: bool = False):
        try:
            import mne
        except ImportError as exc:
            raise RuntimeError("缺少 mne，请运行：py -m pip install mne") from exc

        readers = {
            ".cnt": mne.io.read_raw_cnt,
            ".edf": mne.io.read_raw_edf,
            ".bdf": mne.io.read_raw_bdf,
            ".fif": mne.io.read_raw_fif,
        }
        suffix = file_path.suffix.lower()
        if suffix not in readers:
            raise ValueError(f"暂不支持 {suffix}，当前支持：{sorted(SUPPORTED_EXTENSIONS)}")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return readers[suffix](str(file_path), preload=preload, verbose="ERROR")

    @staticmethod
    def _eeg_picks(raw) -> list[int]:
        try:
            import mne

            picks = list(
                mne.pick_types(raw.info, eeg=True, eog=False, stim=False, exclude="bads")
            )
        except Exception:
            picks = []
        return picks or list(range(len(raw.ch_names)))

    def inspect(self, file_path: Path) -> dict:
        raw = self._open_raw(Path(file_path), preload=False)
        try:
            picks = self._eeg_picks(raw)
            return {
                "file": str(file_path),
                "sample_rate": float(raw.info["sfreq"]),
                "channels": len(picks),
                "duration_sec": float(raw.n_times / raw.info["sfreq"]),
                "channel_names": [raw.ch_names[index] for index in picks],
            }
        finally:
            self._close(raw)

    def load_window(
        self,
        file_path: Path,
        max_duration_sec: float,
        progress: ProgressCallback,
    ) -> EEGRecording:
        file_path = Path(file_path)
        progress("正在读取 EEG 文件头……")
        raw = self._open_raw(file_path, preload=False)
        try:
            sample_rate = float(raw.info["sfreq"])
            picks = self._eeg_picks(raw)
            total_duration = float(raw.n_times / sample_rate)
            stop = min(raw.n_times, max(2, int(max_duration_sec * sample_rate)))
            progress(f"读取前 {stop / sample_rate:.1f} 秒，{len(picks)} 个 EEG 通道……")
            data_volts = raw.get_data(picks=picks, start=0, stop=stop).T
            return EEGRecording(
                source_path=file_path,
                data_uv=np.ascontiguousarray(data_volts * 1e6, dtype=np.float64),
                sample_rate=sample_rate,
                channels=[raw.ch_names[index] for index in picks],
                total_duration_sec=total_duration,
            )
        finally:
            self._close(raw)

    @staticmethod
    def _close(raw) -> None:
        close = getattr(raw, "close", None)
        if callable(close):
            close()
