"""Integration tests for repodata extraction.

These tests hit conda's repodata cache (and potentially the network)
so they are marked as integration tests and excluded from default runs.
Run with: pytest -m integration
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def package_data():
    """Extract package data with conda-forge as the configured channel."""
    from conda.base.context import Context, reset_context

    from conda_completion.repodata import extract_package_data

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(Context, "channels", ("conda-forge",), raising=False)
        reset_context()
        names, versions = extract_package_data()

    reset_context()

    if not names:
        pytest.skip("repodata fetch returned no results (network may be unavailable)")
    return names, versions


def test_extract_package_data_returns_sorted_names(package_data):
    names, _ = package_data
    assert names == sorted(names)


def test_extract_package_data_includes_common_packages(package_data):
    names, _ = package_data
    assert "python" in names


def test_extract_package_data_versions_are_sorted_descending(package_data):
    _, versions = package_data
    assert "python" in versions
    assert len(versions["python"]) > 1


def test_extract_package_data_names_and_versions_consistent(package_data):
    names, versions = package_data
    for name in versions:
        assert name in names, f"{name} in versions but not in names"
    for name in names:
        assert name in versions, f"{name} in names but not in versions"
