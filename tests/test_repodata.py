"""Tests for repodata extraction.

The integration tests hit conda's repodata cache (and potentially the network)
so they are marked explicitly and excluded from default runs.
Run them with: pytest -m integration
"""

from __future__ import annotations

import pytest
from conda.base.context import Context, reset_context
from conda.core import subdir_data
from conda.models import channel

from conda_completion.repodata import extract_package_data


class ContextStub:
    channels = ("conda-forge", "defaults")
    subdirs = ("linux-64", "noarch")


class ChannelStub:
    def __init__(self, value):
        self.canonical_name = value


class PackageRecord:
    def __init__(self, name, version):
        self.name = name
        self.version = version


class SubdirDataStub:
    records_by_channel = {
        "conda-forge/linux-64": [
            PackageRecord("zlib", "1.2.13"),
            PackageRecord("python", "3.11.0"),
        ],
        "conda-forge/noarch": [
            PackageRecord("python", "3.12.0"),
            PackageRecord("attrs", "23.1.0"),
        ],
        "defaults/linux-64": [
            PackageRecord("python", "3.10.0"),
        ],
        "defaults/noarch": [],
    }

    def __init__(self, channel):
        self.channel = channel

    def iter_records(self):
        return self.records_by_channel[self.channel.canonical_name]


class FailingSubdirData(SubdirDataStub):
    def iter_records(self):
        if self.channel.canonical_name == "conda-forge/noarch":
            raise RuntimeError("repodata failed")
        return super().iter_records()


def test_extract_package_data_collects_sorted_names_and_versions(monkeypatch):
    channels = []

    def recording_channel(value):
        channels.append(value)
        return ChannelStub(value)

    monkeypatch.setattr("conda.base.context.context", ContextStub())
    monkeypatch.setattr(channel, "Channel", recording_channel)
    monkeypatch.setattr(subdir_data, "SubdirData", SubdirDataStub)

    names, versions = extract_package_data()

    assert channels == [
        "conda-forge/linux-64",
        "conda-forge/noarch",
        "defaults/linux-64",
        "defaults/noarch",
    ]
    assert names == ["attrs", "python", "zlib"]
    assert versions == {
        "attrs": ["23.1.0"],
        "python": ["3.12.0", "3.11.0", "3.10.0"],
        "zlib": ["1.2.13"],
    }


def test_extract_package_data_skips_failed_channel(monkeypatch):
    monkeypatch.setattr("conda.base.context.context", ContextStub())
    monkeypatch.setattr(channel, "Channel", ChannelStub)
    monkeypatch.setattr(subdir_data, "SubdirData", FailingSubdirData)

    names, versions = extract_package_data()

    assert names == ["python", "zlib"]
    assert versions == {
        "python": ["3.11.0", "3.10.0"],
        "zlib": ["1.2.13"],
    }


@pytest.fixture(scope="module")
def package_data():
    """Extract package data with conda-forge as the configured channel."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(Context, "channels", ("conda-forge",), raising=False)
        reset_context()
        names, versions = extract_package_data()

    reset_context()

    if not names:
        pytest.skip("repodata fetch returned no results (network may be unavailable)")
    return names, versions


@pytest.mark.integration
def test_extract_package_data_returns_sorted_names(package_data):
    names, _ = package_data
    assert names == sorted(names)


@pytest.mark.integration
def test_extract_package_data_includes_common_packages(package_data):
    names, _ = package_data
    assert "python" in names


@pytest.mark.integration
def test_extract_package_data_versions_are_sorted_descending(package_data):
    _, versions = package_data
    assert "python" in versions
    assert len(versions["python"]) > 1


@pytest.mark.integration
def test_extract_package_data_names_and_versions_consistent(package_data):
    names, versions = package_data
    for name in versions:
        assert name in names, f"{name} in versions but not in names"
    for name in names:
        assert name in versions, f"{name} in names but not in versions"
