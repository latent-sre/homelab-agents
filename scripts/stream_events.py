"""Shared parsing for line-delimited JSON emitted by host probe CLIs.

The readers are `fleet.stream`'s; this module keeps the names the probes import.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from fleet import stream as _stream  # noqa: E402

iter_events = _stream.iter_events
iter_content_blocks = _stream.iter_content_blocks
