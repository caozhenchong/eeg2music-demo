#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EEG2Music demo application entry point."""

from __future__ import annotations

from eeg2music.bootstrap import build_application_service
from eeg2music.ui import EEG2MusicGUI


def main() -> int:
    """Build and start the desktop application."""
    app = EEG2MusicGUI(build_application_service())
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
