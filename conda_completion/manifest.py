"""Completion manifest data model and msgpack I/O."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import msgpack

from .exceptions import ManifestError

if TYPE_CHECKING:
    from pathlib import Path

MAX_MANIFEST_SIZE = 50 * 1024 * 1024
MAX_COLLECTION_SIZE = 2_000_000
MAX_VERSION_RECORD_SIZE = 1024 * 1024


@dataclass(frozen=True)
class OptionSpec:
    """Metadata for a single CLI flag/option."""

    short: str | None = None
    choices: list[str] | None = None
    nargs: str | int | None = None
    completion_type: str | None = None
    description: str | None = None
    metavar: str | None = None
    default: str | None = None
    required: bool = False
    group: str | None = None

    def to_dict(self) -> dict:
        result: dict = {}
        if self.short:
            result["short"] = self.short
        if self.choices:
            result["choices"] = self.choices
        if self.nargs is not None:
            result["nargs"] = str(self.nargs)
        if self.completion_type:
            result["completion_type"] = self.completion_type
        if self.description:
            result["description"] = self.description
        if self.metavar:
            result["metavar"] = self.metavar
        if self.default is not None:
            result["default"] = self.default
        if self.required:
            result["required"] = True
        if self.group:
            result["group"] = self.group
        return result

    @classmethod
    def from_dict(cls, data: dict) -> OptionSpec:
        return cls(
            short=data.get("short"),
            choices=data.get("choices"),
            nargs=data.get("nargs"),
            completion_type=data.get("completion_type"),
            description=data.get("description"),
            metavar=data.get("metavar"),
            default=data.get("default"),
            required=data.get("required", False),
            group=data.get("group"),
        )


@dataclass(frozen=True)
class PositionalSpec:
    """Metadata for a positional argument."""

    name: str
    choices: list[str] | None = None
    nargs: str | int | None = None
    completion_type: str | None = None
    description: str | None = None
    metavar: str | None = None

    def to_dict(self) -> dict:
        result: dict = {"name": self.name}
        if self.choices:
            result["choices"] = self.choices
        if self.nargs is not None:
            result["nargs"] = str(self.nargs)
        if self.completion_type:
            result["completion_type"] = self.completion_type
        if self.description:
            result["description"] = self.description
        if self.metavar:
            result["metavar"] = self.metavar
        return result

    @classmethod
    def from_dict(cls, data: dict) -> PositionalSpec:
        return cls(
            name=data["name"],
            choices=data.get("choices"),
            nargs=data.get("nargs"),
            completion_type=data.get("completion_type"),
            description=data.get("description"),
            metavar=data.get("metavar"),
        )


@dataclass(frozen=True)
class CommandSpec:
    """Metadata for a command/subcommand node in the parser tree."""

    summary: str | None = None
    options: dict[str, OptionSpec] = field(default_factory=dict)
    positionals: list[PositionalSpec] = field(default_factory=list)
    subcommands: dict[str, CommandSpec] = field(default_factory=dict)
    exclusive_groups: list[list[str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        result: dict = {}
        if self.summary:
            result["summary"] = self.summary
        if self.options:
            result["options"] = {name: opt.to_dict() for name, opt in self.options.items()}
        if self.positionals:
            result["positionals"] = [pos.to_dict() for pos in self.positionals]
        if self.exclusive_groups:
            result["exclusive_groups"] = self.exclusive_groups
        if self.subcommands:
            result["subcommands"] = {name: sub.to_dict() for name, sub in self.subcommands.items()}
        return result

    @classmethod
    def from_dict(cls, data: dict) -> CommandSpec:
        options = {name: OptionSpec.from_dict(d) for name, d in data.get("options", {}).items()}
        positionals = [PositionalSpec.from_dict(d) for d in data.get("positionals", [])]
        subcommands = {name: cls.from_dict(d) for name, d in data.get("subcommands", {}).items()}
        return cls(
            summary=data.get("summary"),
            options=options,
            positionals=positionals,
            subcommands=subcommands,
            exclusive_groups=data.get("exclusive_groups", []),
        )


@dataclass(frozen=True)
class CompletionManifest:
    """Top-level completion manifest."""

    version: int = 1
    generated_at: str = ""
    plugin_hash: str = ""
    root_options: dict[str, OptionSpec] = field(default_factory=dict)
    commands: dict[str, CommandSpec] = field(default_factory=dict)
    package_names: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        result: dict = {
            "version": self.version,
            "generated_at": self.generated_at,
            "plugin_hash": self.plugin_hash,
        }
        if self.root_options:
            result["root_options"] = {
                name: opt.to_dict() for name, opt in self.root_options.items()
            }
        result["commands"] = {name: cmd.to_dict() for name, cmd in self.commands.items()}
        if self.package_names:
            result["package_names"] = self.package_names
        return result

    @classmethod
    def from_dict(cls, data: dict) -> CompletionManifest:
        root_options = {
            name: OptionSpec.from_dict(d) for name, d in data.get("root_options", {}).items()
        }
        commands = {name: CommandSpec.from_dict(d) for name, d in data.get("commands", {}).items()}
        return cls(
            version=data.get("version", 1),
            generated_at=data.get("generated_at", ""),
            plugin_hash=data.get("plugin_hash", ""),
            root_options=root_options,
            commands=commands,
            package_names=data.get("package_names", []),
        )


def atomic_write(path: Path, data: bytes) -> None:
    """Write data to a file atomically via temp-file-then-rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise OSError(f"refusing to write through symlink: {path}")
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        f.write(data)
        tmp = f.name
    if path.is_symlink():
        os.unlink(tmp)
        raise OSError(f"refusing to write through symlink: {path}")
    os.replace(tmp, path)


def write_manifest(manifest: CompletionManifest, path: Path) -> None:
    """Serialize a CompletionManifest to a msgpack file."""
    atomic_write(path, msgpack.packb(manifest.to_dict()))


def read_manifest(path: Path) -> CompletionManifest:
    """Deserialize a CompletionManifest from a msgpack file."""
    try:
        if path.is_symlink():
            raise ManifestError("refusing to read through symlink")
        size = path.stat().st_size
        if size > MAX_MANIFEST_SIZE:
            raise ManifestError(f"file too large ({size} bytes)")
        data = msgpack.unpackb(
            path.read_bytes(),
            max_str_len=MAX_MANIFEST_SIZE,
            max_bin_len=MAX_MANIFEST_SIZE,
            max_array_len=MAX_COLLECTION_SIZE,
            max_map_len=MAX_COLLECTION_SIZE,
        )
    except (msgpack.UnpackException, ValueError) as exc:
        raise ManifestError(str(exc)) from exc
    if not isinstance(data, dict):
        raise ManifestError("manifest root is not a mapping")
    try:
        return CompletionManifest.from_dict(data)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ManifestError(f"malformed manifest: {exc}") from exc


def write_versions(
    versions: dict[str, list[str]],
    index_path: Path,
    store_path: Path,
) -> None:
    """Serialize package version data to an index and offset-addressed byte store."""
    if index_path.is_symlink():
        raise OSError(f"refusing to write through symlink: {index_path}")
    if store_path.is_symlink():
        raise OSError(f"refusing to write through symlink: {store_path}")

    index: dict[str, tuple[int, int]] = {}
    store = bytearray()
    for package_name, package_versions in versions.items():
        offset = len(store)
        record = msgpack.packb(package_versions)
        if len(record) > MAX_VERSION_RECORD_SIZE:
            raise ManifestError(f"package version data too large for {package_name}")
        store.extend(record)
        index[package_name] = (offset, len(record))

    atomic_write(store_path, bytes(store))
    atomic_write(index_path, msgpack.packb(index))


def read_versions(index_path: Path, store_path: Path) -> dict[str, list[str]]:
    """Deserialize all package version data from an indexed byte store."""
    try:
        index = read_version_index(index_path)
        return {
            package_name: read_package_versions(index_path, store_path, package_name)
            for package_name in index
        }
    except (msgpack.UnpackException, ValueError, FileNotFoundError) as exc:
        raise ManifestError(str(exc)) from exc


def read_package_versions(index_path: Path, store_path: Path, package_name: str) -> list[str]:
    """Deserialize version data for one package from an indexed byte store."""
    if not package_name:
        raise ManifestError("package name is empty")
    index = read_version_index(index_path)
    try:
        offset, length = index[package_name]
    except KeyError as exc:
        raise ManifestError(f"package not found in version index: {package_name}") from exc
    if length > MAX_VERSION_RECORD_SIZE:
        raise ManifestError(f"package version data too large for {package_name}")
    try:
        if store_path.is_symlink():
            raise ManifestError("refusing to read through symlink")
        size = store_path.stat().st_size
        end = offset + length
        if offset < 0 or length < 0 or end > size:
            raise ManifestError("package version index points outside store")
        with store_path.open("rb") as store_file:
            store_file.seek(offset)
            data = msgpack.unpackb(
                store_file.read(length),
                max_str_len=MAX_MANIFEST_SIZE,
                max_bin_len=MAX_MANIFEST_SIZE,
                max_array_len=MAX_COLLECTION_SIZE,
                max_map_len=MAX_COLLECTION_SIZE,
            )
    except (msgpack.UnpackException, ValueError, FileNotFoundError) as exc:
        raise ManifestError(str(exc)) from exc
    if not isinstance(data, list):
        raise ManifestError("package versions root is not a list")
    return data


def read_version_index(index_path: Path) -> dict[str, tuple[int, int]]:
    """Deserialize the package versions offset index."""
    try:
        if index_path.is_symlink():
            raise ManifestError("refusing to read through symlink")
        size = index_path.stat().st_size
        if size > MAX_MANIFEST_SIZE:
            raise ManifestError(f"file too large ({size} bytes)")
        raw_index = msgpack.unpackb(
            index_path.read_bytes(),
            max_str_len=MAX_MANIFEST_SIZE,
            max_bin_len=MAX_MANIFEST_SIZE,
            max_array_len=MAX_COLLECTION_SIZE,
            max_map_len=MAX_COLLECTION_SIZE,
        )
    except (msgpack.UnpackException, ValueError, FileNotFoundError) as exc:
        raise ManifestError(str(exc)) from exc
    if not isinstance(raw_index, dict):
        raise ManifestError("version index root is not a mapping")

    index = {}
    for package_name, record in raw_index.items():
        if not isinstance(package_name, str):
            raise ManifestError("version index package name is not a string")
        if not isinstance(record, (list, tuple)) or len(record) != 2:
            raise ManifestError(f"malformed version index entry for {package_name}")
        offset, length = record
        if not isinstance(offset, int) or not isinstance(length, int):
            raise ManifestError(f"malformed version index entry for {package_name}")
        index[package_name] = (offset, length)
    return index
