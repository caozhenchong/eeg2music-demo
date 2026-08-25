"""Matplotlib chart panel for an EEGResult."""

from __future__ import annotations

import numpy as np

from ..config import EEG_BANDS
from ..domain.models import EEGResult


class ResultCharts:
    """Own the four result plots and keep plotting code out of the window class."""

    TEXT = "#172033"
    MUTED = "#68758A"
    ACCENT = "#2563EB"
    PANEL = "#FFFFFF"

    def __init__(self, parent) -> None:
        import matplotlib

        matplotlib.use("TkAgg")
        matplotlib.rcParams["font.sans-serif"] = [
            "Microsoft YaHei",
            "SimHei",
            "Arial Unicode MS",
        ]
        matplotlib.rcParams["axes.unicode_minus"] = False
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        self.figure = Figure(figsize=(9.2, 5.4), dpi=100, facecolor=self.PANEL)
        self.axes = self.figure.subplots(2, 2)
        self.figure.subplots_adjust(
            left=0.075,
            right=0.975,
            top=0.94,
            bottom=0.10,
            wspace=0.28,
            hspace=0.38,
        )
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.widget = self.canvas.get_tk_widget()
        self.draw_empty()

    def draw_empty(self) -> None:
        titles = [
            "EEG 波形（原始 / 清洗）",
            "平均功率谱",
            "相对频带功率",
            "V-A 情绪空间",
        ]
        for axis, title in zip(self.axes.flat, titles):
            axis.clear()
            axis.set_title(title, fontsize=10, fontweight="bold", color=self.TEXT)
            axis.text(
                0.5,
                0.48,
                "等待运行处理",
                ha="center",
                va="center",
                transform=axis.transAxes,
                color=self.MUTED,
            )
            axis.set_xticks([])
            axis.set_yticks([])
            for spine in axis.spines.values():
                spine.set_color("#DCE3EC")
        self.canvas.draw_idle()

    def draw(self, result: EEGResult) -> None:
        for axis in self.axes.flat:
            axis.clear()
            axis.tick_params(colors=self.MUTED, labelsize=8)
            axis.grid(color="#E8EDF4", linewidth=0.7, alpha=0.9)
            for spine in axis.spines.values():
                spine.set_color("#DCE3EC")

        self._draw_waveform(self.axes[0, 0], result)
        self._draw_psd(self.axes[0, 1], result)
        self._draw_bands(self.axes[1, 0], result)
        self._draw_valence_arousal(self.axes[1, 1], result)
        self.canvas.draw_idle()

    def _draw_waveform(self, axis, result: EEGResult) -> None:
        scale = float(np.nanpercentile(np.abs(result.preview_clean), 90))
        scale = max(scale * 2.5, 10.0)
        offsets = np.arange(result.preview_clean.shape[1])[::-1] * scale
        for index, offset in enumerate(offsets):
            raw_line = result.preview_raw[:, index] - np.nanmedian(
                result.preview_raw[:, index]
            )
            clean_line = result.preview_clean[:, index] - np.nanmedian(
                result.preview_clean[:, index]
            )
            axis.plot(
                result.preview_time,
                raw_line + offset,
                color="#B8C3D5",
                linewidth=0.45,
                alpha=0.65,
            )
            axis.plot(
                result.preview_time,
                clean_line + offset,
                color=self.ACCENT,
                linewidth=0.65,
            )
        axis.set_yticks(offsets)
        axis.set_yticklabels(result.preview_channels)
        axis.set_xlim(result.preview_time[0], result.preview_time[-1])
        axis.set_xlabel("时间 (s)", fontsize=8)
        axis.set_title(
            "EEG 波形：灰=原始，蓝=清洗",
            fontsize=10,
            fontweight="bold",
            color=self.TEXT,
        )

    def _draw_psd(self, axis, result: EEGResult) -> None:
        mask = (result.freqs >= 0.5) & (
            result.freqs <= min(45.0, result.sample_rate / 2.0)
        )
        psd_db = 10.0 * np.log10(np.maximum(result.mean_psd[mask], 1e-12))
        axis.plot(result.freqs[mask], psd_db, color="#7C3AED", linewidth=1.25)
        for low, high in EEG_BANDS.values():
            axis.axvspan(low, high, alpha=0.035, color=self.ACCENT)
        axis.set_xlabel("频率 (Hz)", fontsize=8)
        axis.set_ylabel("PSD (dB μV²/Hz)", fontsize=8)
        iaf = (
            f" · IAF {result.individual_alpha_peak_hz:.2f} Hz"
            if result.individual_alpha_peak_hz
            else ""
        )
        axis.set_title(
            f"平均功率谱{iaf}", fontsize=10, fontweight="bold", color=self.TEXT
        )

    def _draw_bands(self, axis, result: EEGResult) -> None:
        names = list(result.band_relative)
        values = [100.0 * result.band_relative[name] for name in names]
        colors = ["#60A5FA", "#38BDF8", "#34D399", "#F59E0B", "#F472B6"]
        bars = axis.bar(names, values, color=colors, width=0.68)
        maximum = max(values) if values else 1.0
        for bar, value in zip(bars, values):
            axis.text(
                bar.get_x() + bar.get_width() / 2,
                value + maximum * 0.025,
                f"{value:.1f}%",
                ha="center",
                va="bottom",
                fontsize=7,
                color=self.MUTED,
            )
        axis.set_ylabel("相对功率 (%)", fontsize=8)
        axis.set_title("相对频带功率", fontsize=10, fontweight="bold", color=self.TEXT)
        axis.set_ylim(0, maximum * 1.18 if maximum > 0 else 1)

    def _draw_valence_arousal(self, axis, result: EEGResult) -> None:
        axis.axhline(0, color="#94A3B8", linewidth=0.8)
        axis.axvline(0, color="#94A3B8", linewidth=0.8)
        axis.fill_between([0, 1], 0, 1, color="#DCFCE7", alpha=0.55)
        axis.fill_between([-1, 0], 0, 1, color="#FFEDD5", alpha=0.45)
        axis.fill_between([0, 1], -1, 0, color="#E0F2FE", alpha=0.55)
        axis.fill_between([-1, 0], -1, 0, color="#FEE2E2", alpha=0.45)
        axis.scatter(
            [result.valence],
            [result.arousal],
            s=120,
            color=self.ACCENT,
            edgecolor="white",
            linewidth=1.5,
            zorder=5,
        )
        axis.annotate(
            result.emotion_label,
            (result.valence, result.arousal),
            xytext=(8, 8),
            textcoords="offset points",
            fontsize=8,
            color=self.TEXT,
        )
        axis.set_xlim(-1.05, 1.05)
        axis.set_ylim(-1.05, 1.05)
        axis.set_xlabel("Valence 负 ← → 正", fontsize=8)
        axis.set_ylabel("Arousal 低 ← → 高", fontsize=8)
        axis.set_title(
            "V-A 情绪空间（演示映射）",
            fontsize=10,
            fontweight="bold",
            color=self.TEXT,
        )
