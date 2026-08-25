"""Application paths and signal-processing constants."""

from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = Path(r"F:\dataset\eeg_music data\test_data")
OUTPUT_DIR = APP_DIR / "outputs"

SUPPORTED_EXTENSIONS = {".cnt", ".edf", ".bdf", ".fif"}

EEG_BANDS: dict[str, tuple[float, float]] = {
    "Delta": (1.0, 4.0),
    "Theta": (4.0, 8.0),
    "Alpha": (8.0, 13.0),
    "Beta": (13.0, 30.0),
    "Gamma": (30.0, 45.0),
}
