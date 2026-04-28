"""Runtime encoding helpers."""

from __future__ import annotations

import sys


def ensure_utf8_stdio() -> None:
    """Force stdout/stderr to UTF-8 when the stream supports reconfigure()."""

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            # Some embedded terminals or wrapped streams do not support reconfigure().
            continue
