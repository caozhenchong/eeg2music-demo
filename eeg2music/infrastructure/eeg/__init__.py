"""EEG input and signal-analysis infrastructure."""

from .mne_data_source import MNEEEGDataSource
from .scipy_analyzer import SciPyEEGAnalyzer

__all__ = ["MNEEEGDataSource", "SciPyEEGAnalyzer"]
