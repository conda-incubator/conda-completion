"""Unit tests for repodata extraction."""

from __future__ import annotations

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
    monkeypatch.setattr("conda.models.channel.Channel", recording_channel)
    monkeypatch.setattr("conda.core.subdir_data.SubdirData", SubdirDataStub)

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
    monkeypatch.setattr("conda.models.channel.Channel", ChannelStub)
    monkeypatch.setattr("conda.core.subdir_data.SubdirData", FailingSubdirData)

    names, versions = extract_package_data()

    assert names == ["python", "zlib"]
    assert versions == {
        "python": ["3.11.0", "3.10.0"],
        "zlib": ["1.2.13"],
    }
