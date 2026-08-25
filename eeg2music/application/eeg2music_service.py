"""Application service orchestrating the EEG-to-music business workflow."""

from __future__ import annotations

from pathlib import Path

from ..domain.models import EEGResult
from ..domain.ports import (
    BrainStateDecoder,
    EEGAnalyzer,
    EEGDataSource,
    MusicMapper,
    ProgressCallback,
    ResultPublisher,
)


class EEG2MusicApplicationService:
    """Single facade consumed by the presentation layer."""

    def __init__(
        self,
        data_source: EEGDataSource,
        analyzer: EEGAnalyzer,
        brain_state_decoder: BrainStateDecoder,
        music_mapper: MusicMapper,
        result_publisher: ResultPublisher,
    ) -> None:
        self._data_source = data_source
        self._analyzer = analyzer
        self._brain_state_decoder = brain_state_decoder
        self._music_mapper = music_mapper
        self._result_publisher = result_publisher

    def find_files(self, data_dir: Path) -> list[Path]:
        return self._data_source.find_files(data_dir)

    def inspect_file(self, file_path: Path) -> dict:
        return self._data_source.inspect(file_path)

    def analyze_file(
        self,
        file_path: Path,
        max_duration_sec: float = 60.0,
        progress: ProgressCallback | None = None,
        publish_outputs: bool = True,
    ) -> EEGResult:
        progress = progress or (lambda _message: None)
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(file_path)

        recording = self._data_source.load_window(
            file_path,
            max_duration_sec=max_duration_sec,
            progress=progress,
        )
        analysis = self._analyzer.analyze(recording, progress)

        progress("映射 Valence/Arousal 与音乐控制参数……")
        brain_state = self._brain_state_decoder.decode(recording, analysis)
        music = self._music_mapper.map(brain_state, analysis.band_relative)
        result = EEGResult(
            file_path=str(recording.source_path),
            sample_rate=recording.sample_rate,
            channels=recording.channels,
            duration_sec=recording.total_duration_sec,
            analyzed_duration_sec=recording.analyzed_duration_sec,
            bad_channels=[
                name
                for name, is_bad in zip(
                    recording.channels, analysis.bad_channel_mask
                )
                if bool(is_bad)
            ],
            quality_score=analysis.quality_score,
            valence=round(brain_state.valence, 4),
            arousal=round(brain_state.arousal, 4),
            emotion_label=brain_state.label,
            valence_source=brain_state.source,
            band_relative=analysis.band_relative,
            band_absolute=analysis.band_absolute,
            individual_alpha_peak_hz=analysis.individual_alpha_peak_hz,
            processing_info=analysis.processing_info,
            music=music,
            preview_time=analysis.preview_time,
            preview_raw=analysis.preview_raw,
            preview_clean=analysis.preview_clean,
            preview_channels=analysis.preview_channels,
            freqs=analysis.freqs,
            mean_psd=analysis.mean_psd,
        )

        if publish_outputs:
            self._result_publisher.publish(result, file_path, progress)
        progress("处理完成。")
        return result
