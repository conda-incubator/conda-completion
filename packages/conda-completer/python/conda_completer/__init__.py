"""Python API for the conda-completer binary.

Locates the _conda_completer binary installed by maturin.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ON_WIN = sys.platform == "win32"


def find_completer_binary() -> Path:
    """Locate the _conda_completer binary.

    The binary is installed to the environment's scripts directory by maturin.
    For development the cargo target directory is checked as a fallback.
    """
    package_dir = Path(__file__).parent
    prefix = Path(sys.prefix)
    name = "_conda_completer.exe" if _ON_WIN else "_conda_completer"

    candidates = [
        (prefix / "Scripts" / name) if _ON_WIN else (prefix / "bin" / name),
        package_dir / name,
        package_dir.parent.parent / "target" / "release" / name,
        package_dir.parent.parent / "target" / "debug" / name,
    ]
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_file():
            return resolved
    msg = "_conda_completer binary not found"
    raise FileNotFoundError(msg)
