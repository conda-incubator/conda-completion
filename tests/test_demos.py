"""Execute hidden demo setup without recording GIFs."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform == "win32", reason="Demo setup requires a POSIX shell")
@pytest.mark.parametrize(
    ("demo_name", "fixture_name"),
    [
        ("dynamic-completion", "environment.yml"),
        ("workspace-completion", "conda.toml"),
        ("install", None),
        ("quickstart", None),
    ],
)
@pytest.mark.parametrize("allocation_fails", [False, True])
def test_demo_temporary_directories(
    tmp_path: Path, demo_name: str, fixture_name: str | None, allocation_fails: bool
) -> None:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is not installed")

    root = Path(__file__).resolve().parent.parent
    hidden_setup = (root / "demos" / f"{demo_name}.tape").read_text().split("\nShow\n")[0]
    commands = []
    for line in hidden_setup.splitlines():
        if line.startswith("Type "):
            value = line.removeprefix("Type ")
            commands.append(json.loads(value) if value.startswith('"') else value[1:-1])
    setup = "\n".join(commands)
    # Refuse to execute the old setup against the machine's shared /tmp directory.
    assert "/tmp/.demo-" not in setup

    temporary = tmp_path / "temporary directory with spaces"
    temporary.mkdir()
    neighbor = tmp_path / "neighbor"
    neighbor.mkdir()
    sentinel = neighbor / "keep"
    sentinel.write_text("unchanged")
    for name in (".demo-home", ".demo-project"):
        (temporary / name).symlink_to(neighbor, target_is_directory=True)
    original_home = tmp_path / "original-home"
    original_home.mkdir()
    allocated = set()

    for exit_status in (0, 17):
        report = tmp_path / f"report-{exit_status}"
        report.mkdir()
        command_log = report / "commands"
        result = subprocess.run(
            [bash, "--noprofile", "--norc"],
            input="\n".join(
                [
                    "umask 000",
                    "pixi() {\n    :\n}",
                    'conda() {\n    printf \'%s\\t%s\\n\' "$*" "$HOME" >> "$DEMO_COMMAND_LOG"\n}',
                    "clear() {\n    :\n}",
                    setup,
                    'printf \'%s\\n\' "$DEMO_TMPDIR" "$HOME" "$PWD" > "$DEMO_REPORT/state"',
                    'cp -Rp "$DEMO_TMPDIR" "$DEMO_REPORT/snapshot"',
                    f"exit {exit_status}",
                ]
            ),
            env={
                **os.environ,
                "HOME": str(original_home),
                "TMPDIR": str(temporary / "missing" if allocation_fails else temporary),
                "DEMO_PS1": "$ ",
                "DEMO_COMMAND_LOG": str(command_log),
                "DEMO_REPORT": str(report),
            },
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert sentinel.read_text() == "unchanged"
        assert set(neighbor.iterdir()) == {sentinel}
        assert all((temporary / name).is_symlink() for name in (".demo-home", ".demo-project"))
        assert set(temporary.iterdir()) == {
            temporary / ".demo-home",
            temporary / ".demo-project",
        }
        if allocation_fails:
            assert result.returncode != 0
            assert not (report / "state").exists()
            continue

        assert result.returncode == exit_status, result.stderr
        demo_root, home, project = map(Path, (report / "state").read_text().splitlines())
        assert demo_root.parent == temporary
        assert demo_root not in allocated
        allocated.add(demo_root)
        assert not demo_root.exists()
        assert home == demo_root / "home"
        snapshot = report / "snapshot"
        assert stat.S_IMODE(snapshot.stat().st_mode) == 0o700
        if fixture_name is None:
            assert project == root
            assert (snapshot / "home" / ".bashrc").read_text() == ""
        else:
            assert project == demo_root / "project"
            assert (snapshot / "project" / fixture_name).read_bytes() == (
                root / "demos" / "fixtures" / fixture_name
            ).read_bytes()
            assert (
                snapshot / "home" / ".conda" / "environments.txt"
            ).read_text().splitlines() == [
                "/opt/conda/envs/base",
                "/opt/conda/envs/data-science",
                "/opt/conda/envs/web-dev",
            ]
        expected_commands = [
            "completion generate" + ("" if demo_name == "quickstart" else " --no-repodata")
        ]
        if demo_name != "install":
            expected_commands.append("completion init bash")
        expected_home = original_home if fixture_name else home
        assert command_log.read_text().splitlines() == [
            f"{command}\t{expected_home}" for command in expected_commands
        ]
