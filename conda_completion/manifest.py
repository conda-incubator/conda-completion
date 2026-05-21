"""Completion manifest data model and TOML I/O."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w

from .exceptions import ManifestError

if TYPE_CHECKING:
    from pathlib import Path


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
        )


def write_manifest(manifest: CompletionManifest, path: Path) -> None:
    """Serialize a CompletionManifest to a TOML file."""
    data = manifest.to_dict()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomli_w.dumps(data), encoding="utf-8")


def read_manifest(path: Path) -> CompletionManifest:
    """Deserialize a CompletionManifest from a TOML file."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ManifestError(str(exc)) from exc
    return CompletionManifest.from_dict(data)
