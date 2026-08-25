"""Standalone SciPy implementation of preprocessing and EEG feature analysis."""

from __future__ import annotations

import time
import warnings

import numpy as np
from scipy import signal

from ...config import EEG_BANDS
from ...domain.models import EEGAnalysis, EEGRecording
from ...domain.ports import ProgressCallback


class SciPyEEGAnalyzer:
    """Fully local EEG analyzer with no runtime dependency on another project."""

    def __init__(
        self,
        line_frequency: float = 50.0,
        low_cut_hz: float = 0.5,
        high_cut_hz: float = 45.0,
        despike_z: float = 8.0,
    ) -> None:
        self.line_frequency = float(line_frequency)
        self.low_cut_hz = float(low_cut_hz)
        self.high_cut_hz = float(high_cut_hz)
        self.despike_z = float(despike_z)

    def analyze(
        self, recording: EEGRecording, progress: ProgressCallback
    ) -> EEGAnalysis:
        if recording.data_uv.ndim != 2:
            raise ValueError(f"EEG 数据必须为二维矩阵：{recording.data_uv.shape}")
        if recording.data_uv.shape[0] < 8 or recording.data_uv.shape[1] < 1:
            raise ValueError(f"EEG 数据维度异常：{recording.data_uv.shape}")

        progress("坏导检测与 0.5–45 Hz 预处理……")
        bad_mask = self._detect_bad_channels(recording.data_uv)
        clean, processing_info = self._preprocess(
            recording.data_uv, recording.sample_rate, bad_mask
        )

        progress("计算 PSD、频带功率与个体 Alpha 峰……")
        (
            freqs,
            psd,
            band_absolute,
            band_relative,
            channel_absolute,
        ) = self._compute_features(clean, recording.sample_rate)
        quality = self._quality_score(recording.data_uv, bad_mask, processing_info)

        preview_samples = min(
            len(clean), max(8, int(recording.sample_rate * 8.0))
        )
        preview_step = max(1, preview_samples // 2400)
        preview_indices = np.arange(0, preview_samples, preview_step)
        preview_channel_count = min(6, clean.shape[1])

        return EEGAnalysis(
            clean_data=clean,
            bad_channel_mask=bad_mask,
            quality_score=quality,
            band_relative={key: round(value, 6) for key, value in band_relative.items()},
            band_absolute={key: round(value, 6) for key, value in band_absolute.items()},
            channel_band_absolute=channel_absolute,
            individual_alpha_peak_hz=self._individual_alpha_peak(freqs, psd),
            processing_info=processing_info,
            preview_time=preview_indices / recording.sample_rate,
            preview_raw=np.asarray(
                recording.data_uv[preview_indices, :preview_channel_count]
            ),
            preview_clean=np.asarray(clean[preview_indices, :preview_channel_count]),
            preview_channels=recording.channels[:preview_channel_count],
            freqs=np.asarray(freqs),
            mean_psd=np.asarray(np.nanmean(psd, axis=1)),
        )

    @staticmethod
    def _finite_copy(data: np.ndarray) -> tuple[np.ndarray, int]:
        array = np.array(data, dtype=np.float64, order="C", copy=True)
        finite = np.isfinite(array)
        invalid_count = int(array.size - np.count_nonzero(finite))
        if invalid_count == 0:
            return array, 0

        safe = np.where(finite, array, np.nan)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            channel_medians = np.nanmedian(safe, axis=0)
        channel_medians = np.nan_to_num(channel_medians, nan=0.0)
        rows, columns = np.where(~finite)
        array[rows, columns] = channel_medians[columns]
        return array, invalid_count

    @staticmethod
    def _despike(data: np.ndarray, threshold: float) -> tuple[np.ndarray, int]:
        if threshold <= 0:
            return data, 0
        median = np.median(data, axis=0)
        mad = np.median(np.abs(data - median), axis=0)
        robust_sigma = 1.4826 * mad
        fallback_sigma = np.std(data, axis=0)
        robust_sigma = np.where(robust_sigma > 1e-8, robust_sigma, fallback_sigma)
        robust_sigma = np.maximum(robust_sigma, 1e-8)
        lower = median - threshold * robust_sigma
        upper = median + threshold * robust_sigma
        spike_mask = (data < lower) | (data > upper)
        return np.clip(data, lower, upper), int(np.count_nonzero(spike_mask))

    @staticmethod
    def _detect_bad_channels(data_uv: np.ndarray) -> np.ndarray:
        finite = np.nan_to_num(data_uv, nan=0.0, posinf=0.0, neginf=0.0)
        channel_std = np.std(finite, axis=0)
        peak_to_peak = np.ptp(finite, axis=0)
        log_std = np.log(np.maximum(channel_std, 1e-9))
        median = float(np.median(log_std))
        mad = float(np.median(np.abs(log_std - median)))
        robust_z = np.abs(log_std - median) / max(1.4826 * mad, 1e-6)
        return (channel_std < 0.05) | (peak_to_peak > 500.0) | (robust_z > 5.0)

    def _build_filters(self, sample_rate: float) -> tuple[np.ndarray | None, np.ndarray | None]:
        nyquist = sample_rate / 2.0
        notch_sos = None
        bandpass_sos = None
        if 0.0 < self.line_frequency < nyquist * 0.98:
            b_notch, a_notch = signal.iirnotch(
                self.line_frequency, 30.0, sample_rate
            )
            notch_sos = signal.tf2sos(b_notch, a_notch)

        high_cut = min(self.high_cut_hz, nyquist * 0.95)
        if self.low_cut_hz < high_cut:
            bandpass_sos = signal.butter(
                4,
                [self.low_cut_hz, high_cut],
                btype="bandpass",
                fs=sample_rate,
                output="sos",
            )
        return notch_sos, bandpass_sos

    @staticmethod
    def _apply_filter(
        sos: np.ndarray | None, data: np.ndarray
    ) -> tuple[np.ndarray, str]:
        if sos is None or data.shape[0] < 2:
            return data, "skipped"
        try:
            return signal.sosfiltfilt(sos, data, axis=0), "zero-phase"
        except ValueError:
            return signal.sosfilt(sos, data, axis=0), "causal-short-window"

    def _preprocess(
        self, data_uv: np.ndarray, sample_rate: float, bad_mask: np.ndarray
    ) -> tuple[np.ndarray, dict]:
        started = time.perf_counter()
        clean, invalid_count = self._finite_copy(data_uv)
        raw_rms = float(np.sqrt(np.mean(np.square(clean)))) if clean.size else 0.0
        baseline = np.median(clean, axis=0, keepdims=True)
        centered = clean - baseline
        clipped, spike_count = self._despike(centered, self.despike_z)
        notch_sos, bandpass_sos = self._build_filters(sample_rate)
        notch_clean, notch_mode = self._apply_filter(notch_sos, clipped)
        filtered, band_mode = self._apply_filter(bandpass_sos, notch_clean)
        filtered = np.nan_to_num(filtered, nan=0.0, posinf=0.0, neginf=0.0)

        good_indices = np.flatnonzero(~bad_mask)
        if len(good_indices) < 2:
            good_indices = np.arange(filtered.shape[1])
        reference = np.mean(filtered[:, good_indices], axis=1, keepdims=True)
        output = np.ascontiguousarray(filtered - reference, dtype=np.float32)

        clean_rms = float(np.sqrt(np.mean(np.square(output)))) if output.size else 0.0
        removed_rms = (
            float(np.sqrt(np.mean(np.square(centered - output))))
            if output.size
            else 0.0
        )
        filter_mode = (
            band_mode if notch_mode == band_mode else f"{notch_mode}/{band_mode}"
        )
        return output, {
            "implementation": "standalone scipy analyzer",
            "line_freq_hz": self.line_frequency,
            "band_hz": [self.low_cut_hz, self.high_cut_hz],
            "invalid_samples": invalid_count,
            "spike_ratio": spike_count / max(1, clean.size),
            "raw_rms_uv": raw_rms,
            "clean_rms_uv": clean_rms,
            "removed_rms_uv": removed_rms,
            "filter_mode": filter_mode,
            "reference": "CAR",
            "elapsed_ms": (time.perf_counter() - started) * 1000.0,
        }

    @staticmethod
    def _compute_features(
        clean: np.ndarray, sample_rate: float
    ) -> tuple[
        np.ndarray,
        np.ndarray,
        dict[str, float],
        dict[str, float],
        dict[str, np.ndarray],
    ]:
        freqs, psd = signal.welch(
            clean,
            fs=sample_rate,
            nperseg=min(len(clean), max(32, int(sample_rate * 2))),
            axis=0,
        )
        integrate = getattr(np, "trapezoid", None)
        if integrate is None:
            integrate = np.trapz

        band_absolute: dict[str, float] = {}
        channel_absolute: dict[str, np.ndarray] = {}
        for name, (low, high) in EEG_BANDS.items():
            mask = (freqs >= low) & (freqs < high)
            if np.count_nonzero(mask) >= 2:
                values = integrate(psd[mask, :], freqs[mask], axis=0)
            else:
                values = np.zeros(clean.shape[1], dtype=float)
            values = np.maximum(np.asarray(values, dtype=float), 0.0)
            channel_absolute[name] = values
            band_absolute[name] = float(np.mean(values))

        total_power = sum(band_absolute.values()) or 1.0
        band_relative = {
            name: float(value / total_power) for name, value in band_absolute.items()
        }
        return freqs, psd, band_absolute, band_relative, channel_absolute

    @staticmethod
    def _quality_score(
        raw_uv: np.ndarray, bad_mask: np.ndarray, processing_info: dict
    ) -> float:
        finite_ratio = float(np.mean(np.isfinite(raw_uv)))
        good_ratio = float(1.0 - np.mean(bad_mask))
        p95 = float(np.nanpercentile(np.abs(raw_uv), 95))
        amplitude_score = float(
            np.clip(1.0 - max(0.0, p95 - 80.0) / 320.0, 0.0, 1.0)
        )
        spike_ratio = float(processing_info.get("spike_ratio", 0.0) or 0.0)
        spike_score = float(np.clip(1.0 - spike_ratio * 25.0, 0.0, 1.0))
        score = 100.0 * (
            0.45 * good_ratio
            + 0.25 * amplitude_score
            + 0.20 * spike_score
            + 0.10 * finite_ratio
        )
        return round(float(np.clip(score, 0.0, 100.0)), 1)

    @staticmethod
    def _individual_alpha_peak(
        freqs: np.ndarray, psd: np.ndarray
    ) -> float | None:
        mask = (freqs >= 7.0) & (freqs <= 14.0)
        if not np.any(mask):
            return None
        curve = np.nanmean(psd[mask, :], axis=1)
        if not np.isfinite(curve).any():
            return None
        return round(float(freqs[mask][int(np.nanargmax(curve))]), 2)
