"""Tests for the refresh CLI subcommand."""

from __future__ import annotations

import argparse

from conda_completion.cli.refresh import execute_refresh


def test_execute_refresh_forces_package_metadata_refresh(monkeypatch):
    calls = []

    def record_write(args, *, refresh, include):
        calls.append((args, refresh, include))
        return 0

    monkeypatch.setattr("conda_completion.cli.refresh.write_completion_data", record_write)

    args = argparse.Namespace()
    result = execute_refresh(args)

    assert result == 0
    assert calls == [(args, True, True)]
