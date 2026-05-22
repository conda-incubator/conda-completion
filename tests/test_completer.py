"""Integration tests for the _conda_completer Rust binary."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import msgpack
import pytest

COMPLETER_BINARY = (
    Path(__file__).parent.parent
    / "target"
    / "release"
    / ("_conda_completer.exe" if sys.platform == "win32" else "_conda_completer")
)


@pytest.fixture()
def sample_manifest(tmp_path):
    """Create a minimal completion.msgpack for testing."""
    manifest = {
        "version": 1,
        "generated_at": "2025-01-01T00:00:00Z",
        "plugin_hash": "test",
        "root_options": {
            "--verbose": {
                "short": "-v",
                "description": "Use once for info, twice for debug",
            },
            "--json": {
                "description": "Report all output as json",
            },
        },
        "commands": {
            "install": {
                "summary": "Install packages",
                "options": {
                    "--name": {
                        "short": "-n",
                        "completion_type": "env_name",
                        "description": "Name of environment",
                    },
                    "--channel": {
                        "short": "-c",
                        "completion_type": "channel",
                        "description": "Additional channel",
                    },
                    "--dry-run": {
                        "description": "Only display what would be done",
                    },
                },
            },
            "workspace": {
                "summary": "Manage workspaces",
                "subcommands": {
                    "install": {"summary": "Install workspace"},
                    "list": {"summary": "List environments"},
                },
            },
            "create": {
                "summary": "Create an environment",
            },
        },
    }
    path = tmp_path / "completion.msgpack"
    path.write_bytes(msgpack.packb(manifest))
    return path


@pytest.fixture()
def project_dir(tmp_path):
    """Create a project directory with a conda.toml."""
    conda_toml = {
        "workspace": {"channels": ["conda-forge", "defaults"]},
        "environments": {
            "dev": {},
            "test": {},
            "prod": {},
        },
        "tasks": {
            "build": "cargo build",
            "test": "pytest",
            "lint": "ruff check .",
        },
    }
    import tomli_w

    (tmp_path / "conda.toml").write_text(tomli_w.dumps(conda_toml), encoding="utf-8")
    return tmp_path


def _run_completer(manifest_path, shell, words, cword, *, cwd=None):
    """Invoke _conda_completer and return the output lines."""
    if not COMPLETER_BINARY.exists():
        pytest.skip("completer binary not built")

    cmd = [
        str(COMPLETER_BINARY),
        "--shell",
        shell,
        "--manifest",
        str(manifest_path),
        "--",
        *words,
        str(cword),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, cwd=cwd)
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.strip().split("\n") if line]


def test_complete_top_level_commands(sample_manifest):
    lines = _run_completer(sample_manifest, "bash", ["conda", ""], 1)

    names = set(lines)
    assert "install" in names
    assert "workspace" in names
    assert "create" in names


def test_complete_subcommands(sample_manifest):
    lines = _run_completer(sample_manifest, "bash", ["conda", "workspace", ""], 2)

    names = set(lines)
    assert "install" in names
    assert "list" in names


def test_complete_flags(sample_manifest):
    lines = _run_completer(sample_manifest, "bash", ["conda", "install", "--"], 2)

    names = set(lines)
    assert "--name" in names or "-n" in names
    assert "--channel" in names or "-c" in names
    assert "--dry-run" in names


def test_complete_root_flags(sample_manifest):
    lines = _run_completer(sample_manifest, "bash", ["conda", "--"], 1)

    names = set(lines)
    assert "--verbose" in names or "-v" in names
    assert "--json" in names


def test_prefix_filtering(sample_manifest):
    lines = _run_completer(sample_manifest, "bash", ["conda", "inst"], 1)

    assert "install" in lines
    assert "workspace" not in lines
    assert "create" not in lines


def test_zsh_format_includes_descriptions(sample_manifest):
    lines = _run_completer(sample_manifest, "zsh", ["conda", ""], 1)

    found_desc = any(":" in line for line in lines)
    assert found_desc, f"Expected zsh format with descriptions, got: {lines}"


def test_powershell_format_includes_descriptions(sample_manifest):
    lines = _run_completer(sample_manifest, "powershell", ["conda", ""], 1)

    found_desc = any("\t" in line for line in lines)
    assert found_desc, f"Expected PowerShell tab-separated descriptions, got: {lines}"


@pytest.fixture()
def dynamic_manifest(tmp_path):
    """Manifest with env_name, channel, and task_name completion types."""
    manifest = {
        "version": 1,
        "generated_at": "2025-01-01T00:00:00Z",
        "plugin_hash": "test",
        "commands": {
            "install": {
                "summary": "Install packages",
                "options": {
                    "--name": {
                        "short": "-n",
                        "completion_type": "env_name",
                        "description": "Name of environment",
                    },
                    "--channel": {
                        "short": "-c",
                        "completion_type": "channel",
                        "description": "Additional channel",
                    },
                },
            },
            "task": {
                "summary": "Run tasks",
                "subcommands": {
                    "run": {
                        "summary": "Run a task",
                        "positionals": [{"name": "task_name", "completion_type": "task_name"}],
                    },
                },
            },
        },
    }
    path = tmp_path / "completion.msgpack"
    path.write_bytes(msgpack.packb(manifest))
    return path


@pytest.fixture()
def anaconda_project_dir(tmp_path):
    (tmp_path / "anaconda-project.yml").write_text(
        "name: myproject\n"
        "env_specs:\n"
        "  default:\n"
        "    packages: []\n"
        "  production:\n"
        "    packages: []\n"
        "commands:\n"
        "  notebook:\n"
        "    notebook: analysis.ipynb\n"
        "  serve:\n"
        "    unix: python -m http.server\n",
        encoding="utf-8",
    )
    return tmp_path


def test_anaconda_project_env_names(dynamic_manifest, anaconda_project_dir):
    lines = _run_completer(
        dynamic_manifest,
        "bash",
        ["conda", "install", "--name", ""],
        3,
        cwd=anaconda_project_dir,
    )
    assert "default" in lines
    assert "production" in lines


def test_anaconda_project_task_names(dynamic_manifest, anaconda_project_dir):
    lines = _run_completer(
        dynamic_manifest,
        "bash",
        ["conda", "task", "run", ""],
        3,
        cwd=anaconda_project_dir,
    )
    assert "notebook" in lines
    assert "serve" in lines


@pytest.fixture()
def conda_project_dir(tmp_path):
    (tmp_path / "conda-project.yml").write_text(
        "name: projspec\n"
        "environments:\n"
        "  default:\n"
        "    - environment.yml\n"
        "  staging:\n"
        "    - staging.yml\n"
        "commands:\n"
        "  test: pytest\n"
        "  lint: ruff check .\n",
        encoding="utf-8",
    )
    return tmp_path


def test_conda_project_env_names(dynamic_manifest, conda_project_dir):
    lines = _run_completer(
        dynamic_manifest,
        "bash",
        ["conda", "install", "--name", ""],
        3,
        cwd=conda_project_dir,
    )
    assert "default" in lines
    assert "staging" in lines


def test_conda_project_task_names(dynamic_manifest, conda_project_dir):
    lines = _run_completer(
        dynamic_manifest,
        "bash",
        ["conda", "task", "run", ""],
        3,
        cwd=conda_project_dir,
    )
    assert "test" in lines
    assert "lint" in lines


@pytest.fixture()
def conda_lock_dir(tmp_path):
    (tmp_path / "conda.toml").write_text(
        '[workspace]\nchannels = ["conda-forge"]\n[environments]\ndefault = {}\n',
        encoding="utf-8",
    )
    (tmp_path / "conda-lock.yml").write_text(
        "metadata:\n"
        "  channels:\n"
        "  - url: conda-forge\n"
        "  - url: bioconda\n"
        "  platforms:\n"
        "  - linux-64\n"
        "package:\n"
        "- name: python\n"
        "  manager: conda\n",
        encoding="utf-8",
    )
    return tmp_path


def test_conda_lock_channels(dynamic_manifest, conda_lock_dir):
    lines = _run_completer(
        dynamic_manifest,
        "bash",
        ["conda", "install", "--channel", ""],
        3,
        cwd=conda_lock_dir,
    )
    assert "conda-forge" in lines
    assert "bioconda" in lines


@pytest.fixture()
def rattler_lock_dir(tmp_path):
    (tmp_path / "conda.toml").write_text(
        '[workspace]\nchannels = ["conda-forge"]\n[environments]\ndefault = {}\n',
        encoding="utf-8",
    )
    (tmp_path / "conda.lock").write_text(
        "version: 1\n"
        "environments:\n"
        "  default:\n"
        "    channels:\n"
        "    - url: https://conda.anaconda.org/conda-forge/\n"
        "    packages:\n"
        "      osx-arm64:\n"
        "      - conda: https://example.com/pkg.conda\n"
        "  test:\n"
        "    channels:\n"
        "    - url: https://conda.anaconda.org/bioconda/\n"
        "    packages:\n"
        "      osx-arm64:\n"
        "      - conda: https://example.com/pkg2.conda\n",
        encoding="utf-8",
    )
    return tmp_path


def test_rattler_lock_env_names(dynamic_manifest, rattler_lock_dir):
    lines = _run_completer(
        dynamic_manifest,
        "bash",
        ["conda", "install", "--name", ""],
        3,
        cwd=rattler_lock_dir,
    )
    assert "default" in lines
    assert "test" in lines


def test_rattler_lock_channels(dynamic_manifest, rattler_lock_dir):
    lines = _run_completer(
        dynamic_manifest,
        "bash",
        ["conda", "install", "--channel", ""],
        3,
        cwd=rattler_lock_dir,
    )
    assert "https://conda.anaconda.org/conda-forge/" in lines
    assert "https://conda.anaconda.org/bioconda/" in lines


def test_pixi_lock_fallback(dynamic_manifest, tmp_path):
    (tmp_path / "pixi.toml").write_text(
        '[workspace]\nchannels = ["conda-forge"]\n[environments]\ndefault = {}\n',
        encoding="utf-8",
    )
    (tmp_path / "pixi.lock").write_text(
        "version: 7\n"
        "environments:\n"
        "  default:\n"
        "    channels:\n"
        "    - url: https://conda.anaconda.org/conda-forge/\n"
        "    packages:\n"
        "      linux-64:\n"
        "      - conda: https://example.com/pkg.conda\n"
        "  docs:\n"
        "    channels:\n"
        "    - url: https://conda.anaconda.org/conda-forge/\n"
        "    packages:\n"
        "      linux-64:\n"
        "      - conda: https://example.com/pkg2.conda\n",
        encoding="utf-8",
    )

    lines = _run_completer(
        dynamic_manifest,
        "bash",
        ["conda", "install", "--name", ""],
        3,
        cwd=tmp_path,
    )
    assert "default" in lines
    assert "docs" in lines
