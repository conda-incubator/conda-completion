"""Root test configuration for conda-completion."""

from __future__ import annotations

import pytest
import shellingham


@pytest.fixture
def shellingham_fails(monkeypatch):
    """Make shellingham.detect_shell raise ShellDetectionFailure."""

    def _fail():
        raise shellingham.ShellDetectionFailure()

    monkeypatch.setattr(shellingham, "detect_shell", _fail)
