"""Main Tkinter window and background-worker coordination."""

from __future__ import annotations

import os
import queue
import threading
import traceback
from pathlib import Path

from ..application import EEG2MusicApplicationService
from ..config import DEFAULT_DATA_DIR
from ..domain.models import EEGResult
from .charts import ResultCharts


class EEG2MusicGUI:
    """Data loading, processing controls, status feedback and result display."""

    BG = "#F4F7FB"
    PANEL = "#FFFFFF"
    TEXT = "#172033"
    MUTED = "#68758A"
    ACCENT = "#2563EB"

    def __init__(self, application: EEG2MusicApplicationService) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.application = application
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.files: list[Path] = []
        self.result: EEGResult | None = None
        self.busy = False

        self.root = tk.Tk()
        self.root.title("EEG2Music Demo · 脑波音乐演示")
        self.root.geometry("1380x860")
        self.root.minsize(1100, 700)
        self.root.configure(bg=self.BG)

        self.data_dir_var = tk.StringVar(value=str(DEFAULT_DATA_DIR))
        self.status_var = tk.StringVar(value="就绪")
        self.file_info_var = tk.StringVar(value="尚未选择数据")
        self.quality_var = tk.StringVar(value="--")
        self.emotion_var = tk.StringVar(value="--")
        self.va_var = tk.StringVar(value="V -- / A --")
        self.music_var = tk.StringVar(value="--")
        self.duration_var = tk.StringVar(value="60")

        self._configure_styles()
        self._build_layout()
        self.root.after(150, self._poll_events)
        self.root.after(250, self.scan_data)

    def _configure_styles(self) -> None:
        style = self.ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background=self.BG)
        style.configure("Panel.TFrame", background=self.PANEL)
        style.configure(
            "Title.TLabel",
            background=self.BG,
            foreground=self.TEXT,
            font=("Microsoft YaHei UI", 19, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=self.BG,
            foreground=self.MUTED,
            font=("Microsoft YaHei UI", 10),
        )
        style.configure(
            "Section.TLabel",
            background=self.PANEL,
            foreground=self.TEXT,
            font=("Microsoft YaHei UI", 11, "bold"),
        )
        style.configure(
            "Body.TLabel",
            background=self.PANEL,
            foreground=self.MUTED,
            font=("Microsoft YaHei UI", 9),
        )
        style.configure(
            "Metric.TLabel",
            background=self.PANEL,
            foreground=self.TEXT,
            font=("Microsoft YaHei UI", 12, "bold"),
        )
        style.configure(
            "Accent.TButton",
            font=("Microsoft YaHei UI", 10, "bold"),
            foreground="white",
            background=self.ACCENT,
            padding=(12, 9),
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#1D4ED8"), ("disabled", "#9CB8F3")],
        )
        style.configure("TButton", font=("Microsoft YaHei UI", 9), padding=(8, 6))
        style.configure("TEntry", padding=6)
        style.configure("Horizontal.TProgressbar", background=self.ACCENT)

    def _build_layout(self) -> None:
        tk, ttk = self.tk, self.ttk
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=(24, 18, 24, 10))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header, text="EEG2Music 脑波音乐演示", style="Title.TLabel"
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="EEG 预处理 · 质量控制 · V-A 情绪语义 · 可解释音乐条件 · MIDI 输出",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(
            header,
            text="处理引擎：独立本地实现",
            style="Subtitle.TLabel",
        ).grid(row=0, column=1, rowspan=2, sticky="e")

        content = ttk.Frame(self.root, padding=(24, 8, 24, 22))
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, minsize=350)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        left = ttk.Frame(content, style="Panel.TFrame", padding=16)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(3, weight=1)
        self._build_data_panel(left)
        self._build_run_panel(left)

        right = ttk.Frame(content, style="Panel.TFrame", padding=16)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)
        self._build_result_panel(right)

    def _build_data_panel(self, parent) -> None:
        tk, ttk = self.tk, self.ttk
        ttk.Label(parent, text="1  加载数据", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        path_row = ttk.Frame(parent, style="Panel.TFrame")
        path_row.grid(row=1, column=0, sticky="ew", pady=(8, 8))
        path_row.columnconfigure(0, weight=1)
        ttk.Entry(path_row, textvariable=self.data_dir_var).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(path_row, text="浏览", command=self.browse_directory).grid(
            row=0, column=1
        )
        ttk.Button(parent, text="加载数据", command=self.scan_data).grid(
            row=2, column=0, sticky="ew", pady=(0, 8)
        )

        list_frame = ttk.Frame(parent, style="Panel.TFrame")
        list_frame.grid(row=3, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.file_list = tk.Listbox(
            list_frame,
            activestyle="none",
            selectmode=tk.BROWSE,
            borderwidth=1,
            relief="solid",
            highlightthickness=0,
            font=("Cascadia Mono", 9),
            foreground=self.TEXT,
            background="#F8FAFC",
            selectbackground=self.ACCENT,
            selectforeground="white",
            exportselection=False,
        )
        scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.file_list.yview
        )
        self.file_list.configure(yscrollcommand=scrollbar.set)
        self.file_list.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.file_list.bind("<<ListboxSelect>>", self._on_file_selected)
        ttk.Label(
            parent,
            textvariable=self.file_info_var,
            style="Body.TLabel",
            wraplength=318,
        ).grid(row=4, column=0, sticky="ew", pady=(8, 12))

    def _build_run_panel(self, parent) -> None:
        ttk = self.ttk
        settings = ttk.Frame(parent, style="Panel.TFrame")
        settings.grid(row=5, column=0, sticky="ew")
        settings.columnconfigure(1, weight=1)
        ttk.Label(settings, text="2  运行处理", style="Section.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        ttk.Label(settings, text="分析时长（秒）", style="Body.TLabel").grid(
            row=1, column=0, sticky="w"
        )
        ttk.Spinbox(
            settings,
            from_=4,
            to=300,
            increment=5,
            textvariable=self.duration_var,
            width=8,
        ).grid(row=1, column=1, sticky="e")
        self.run_button = ttk.Button(
            settings,
            text="运行 EEG2Music",
            style="Accent.TButton",
            command=self.run_processing,
        )
        self.run_button.grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(10, 6)
        )
        self.progress = ttk.Progressbar(settings, mode="indeterminate")
        self.progress.grid(row=3, column=0, columnspan=2, sticky="ew")
        ttk.Label(
            settings,
            textvariable=self.status_var,
            style="Body.TLabel",
            wraplength=318,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(5, 8))

        buttons = ttk.Frame(settings, style="Panel.TFrame")
        buttons.grid(row=5, column=0, columnspan=2, sticky="ew")
        buttons.columnconfigure((0, 1), weight=1)
        self.open_midi_button = ttk.Button(
            buttons, text="打开 MIDI", command=self.open_midi, state="disabled"
        )
        self.open_midi_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.open_json_button = ttk.Button(
            buttons, text="查看 JSON", command=self.open_json, state="disabled"
        )
        self.open_json_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))

    def _build_result_panel(self, parent) -> None:
        ttk = self.ttk
        metrics = ttk.Frame(parent, style="Panel.TFrame")
        metrics.grid(row=0, column=0, sticky="ew")
        for index in range(4):
            metrics.columnconfigure(index, weight=1)
        self._metric(metrics, 0, "信号质量", self.quality_var)
        self._metric(metrics, 1, "脑状态", self.emotion_var)
        self._metric(metrics, 2, "V-A 坐标", self.va_var)
        self._metric(metrics, 3, "音乐控制", self.music_var)

        ttk.Separator(parent, orient="horizontal").grid(
            row=1, column=0, sticky="ew", pady=12
        )
        self.charts = ResultCharts(parent)
        self.charts.widget.grid(row=2, column=0, sticky="nsew")

        log_frame = ttk.Frame(parent, style="Panel.TFrame")
        log_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        ttk.Label(log_frame, text="状态日志", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        from tkinter.scrolledtext import ScrolledText

        self.log = ScrolledText(
            log_frame,
            height=5,
            wrap="word",
            font=("Cascadia Mono", 8),
            foreground="#334155",
            background="#F8FAFC",
            borderwidth=1,
            relief="solid",
        )
        self.log.grid(row=1, column=0, sticky="ew")
        self.log.configure(state="disabled")
        self._append_log(
            "GUI 已启动。情绪解码与音乐旋律为 Demo 映射，可替换为实际模型。"
        )

    def _metric(self, parent, column: int, title: str, variable) -> None:
        frame = self.ttk.Frame(parent, style="Panel.TFrame", padding=(8, 4))
        frame.grid(row=0, column=column, sticky="nsew")
        self.ttk.Label(frame, text=title, style="Body.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.ttk.Label(
            frame, textvariable=variable, style="Metric.TLabel", wraplength=200
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

    def browse_directory(self) -> None:
        from tkinter import filedialog

        selected = filedialog.askdirectory(
            initialdir=self.data_dir_var.get() or str(DEFAULT_DATA_DIR)
        )
        if selected:
            self.data_dir_var.set(selected)
            self.scan_data()

    def scan_data(self) -> None:
        data_path = Path(self.data_dir_var.get().strip().strip('"'))
        self.files = self.application.find_files(data_path)
        self.file_list.delete(0, self.tk.END)
        for path in self.files:
            self.file_list.insert(self.tk.END, path.name)
        if self.files:
            self.file_list.selection_set(0)
            self.file_list.activate(0)
            self._on_file_selected()
            self.status_var.set(f"已加载 {len(self.files)} 个 EEG 文件")
            self._append_log(
                f"数据目录：{data_path}；发现 {len(self.files)} 个支持文件。"
            )
        else:
            self.file_info_var.set("未找到 .cnt / .edf / .bdf / .fif 文件")
            self.status_var.set(f"路径不存在或没有支持的 EEG 文件：{data_path}")
            self._append_log(self.status_var.get())

    def _selected_file(self) -> Path | None:
        selection = self.file_list.curselection()
        if not selection:
            return None
        index = int(selection[0])
        return self.files[index] if 0 <= index < len(self.files) else None

    def _on_file_selected(self, _event=None) -> None:
        path = self._selected_file()
        if path is None:
            return
        size_mb = path.stat().st_size / (1024 * 1024)
        self.file_info_var.set(
            f"{path.name}\n{size_mb:.2f} MB · 点击“运行”读取并处理"
        )

    def run_processing(self) -> None:
        if self.busy:
            return
        path = self._selected_file()
        if path is None:
            self.status_var.set("请先加载并选择 EEG 文件")
            return
        try:
            duration = float(self.duration_var.get())
            if duration < 4:
                raise ValueError
        except ValueError:
            self.status_var.set("分析时长需为不小于 4 的数字")
            return

        self.busy = True
        self.run_button.configure(state="disabled")
        self.open_midi_button.configure(state="disabled")
        self.open_json_button.configure(state="disabled")
        self.progress.start(12)
        self.status_var.set("正在启动后台处理……")
        self._append_log(f"开始处理：{path.name}（最多 {duration:g} 秒）")

        def worker() -> None:
            try:
                result = self.application.analyze_file(
                    path,
                    max_duration_sec=duration,
                    progress=lambda message: self.events.put(("progress", message)),
                    publish_outputs=True,
                )
                self.events.put(("done", result))
            except Exception:
                self.events.put(("error", traceback.format_exc()))

        threading.Thread(
            target=worker, name="EEG2MusicWorker", daemon=True
        ).start()

    def _poll_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "progress":
                    self.status_var.set(str(payload))
                    self._append_log(str(payload))
                elif event == "done":
                    self._processing_done(payload)
                elif event == "error":
                    self._processing_error(str(payload))
        except queue.Empty:
            pass
        self.root.after(120, self._poll_events)

    def _processing_done(self, result: EEGResult) -> None:
        self.busy = False
        self.progress.stop()
        self.run_button.configure(state="normal")
        self.result = result
        self.quality_var.set(f"{result.quality_score:.1f} / 100")
        self.emotion_var.set(result.emotion_label)
        self.va_var.set(f"V {result.valence:+.2f} / A {result.arousal:+.2f}")
        self.music_var.set(
            f"{result.music.tempo_bpm} BPM · {result.music.display_key}"
        )
        self.file_info_var.set(
            f"{Path(result.file_path).name}\n"
            f"{len(result.channels)} ch · {result.sample_rate:g} Hz · "
            f"总计 {result.duration_sec:.1f}s / 分析 {result.analyzed_duration_sec:.1f}s"
        )
        self.status_var.set("处理完成，已生成 MIDI 和 JSON")
        if result.midi_path:
            self.open_midi_button.configure(state="normal")
        if result.json_path:
            self.open_json_button.configure(state="normal")
        self._append_log(
            f"完成：质量 {result.quality_score:.1f}，{result.emotion_label}，"
            f"{result.music.tempo_bpm} BPM / {result.music.display_key}。"
        )
        if result.bad_channels:
            self._append_log("疑似坏导：" + ", ".join(result.bad_channels))
        self.charts.draw(result)

    def _processing_error(self, details: str) -> None:
        self.busy = False
        self.progress.stop()
        self.run_button.configure(state="normal")
        last_line = details.strip().splitlines()[-1] if details.strip() else "未知错误"
        self.status_var.set(f"处理失败：{last_line}")
        self._append_log(details)

    def open_midi(self) -> None:
        if self.result and self.result.midi_path:
            self._open_path(Path(self.result.midi_path))

    def open_json(self) -> None:
        if self.result and self.result.json_path:
            self._open_path(Path(self.result.json_path))

    @staticmethod
    def _open_path(path: Path) -> None:
        if not path.exists():
            return
        if hasattr(os, "startfile"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            import subprocess

            subprocess.Popen(["xdg-open", str(path)])

    def _append_log(self, message: str) -> None:
        if not hasattr(self, "log"):
            return
        self.log.configure(state="normal")
        self.log.insert(self.tk.END, message.rstrip() + "\n")
        self.log.see(self.tk.END)
        self.log.configure(state="disabled")

    def mainloop(self) -> None:
        self.root.mainloop()
