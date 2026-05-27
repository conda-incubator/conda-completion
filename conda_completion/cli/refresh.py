"""``conda completion refresh`` -- force package metadata refresh."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .generate import write_completion_data

if TYPE_CHECKING:
    import argparse


def execute_refresh(args: argparse.Namespace) -> int:
    """Refresh completion data from conda repodata."""
    return write_completion_data(args, refresh=True, include=True)
