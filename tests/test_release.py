"""Exercise draft creation and failed uploads without contacting GitHub."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from ruamel.yaml import YAML

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.mark.skipif(sys.platform == "win32", reason="Release jobs run in Bash on Linux")
@pytest.mark.parametrize(
    "failure",
    [None, "missing-wheel", "wrong-version", "extra-file", "existing-release", "create", "upload"],
)
def test_release_draft_upload(
    tmp_path: Path, native_shell: Callable[[str], str], failure: str | None
) -> None:
    root = Path(__file__).resolve().parent.parent
    workflow = YAML(typ="safe").load(root / ".github/workflows/release.yml")
    script = workflow["jobs"]["create-draft-release"]["steps"][-1]["run"]
    dist = tmp_path / "dist"
    dist.mkdir()
    platforms = [
        "macosx_10_12_x86_64",
        "macosx_11_0_arm64",
        "manylinux_2_17_x86_64.manylinux2014_x86_64",
        "manylinux_2_17_aarch64.manylinux2014_aarch64",
        "win_amd64",
    ]
    filenames = [f"conda_completer-0.3.2-py3-none-{platform}.whl" for platform in platforms]
    filenames.extend(
        [
            "conda_completer-0.3.2.tar.gz",
            "conda_completion-0.3.2.tar.gz",
            "conda_completion-0.3.2-py3-none-any.whl",
        ]
    )
    for filename in filenames:
        (dist / filename).touch()
    if failure == "missing-wheel":
        (dist / filenames[0]).unlink()
    elif failure == "extra-file":
        (dist / "unexpected.txt").touch()

    state = tmp_path / "release-state"
    if failure == "existing-release":
        state.write_text("keep existing release")
    log = tmp_path / "commands"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_gh = bin_dir / "gh"
    fake_gh.write_text(
        f"#!{sys.executable}\n"
        """
from __future__ import annotations

import os
import sys
from pathlib import Path

command = sys.argv[2]
with Path(os.environ["RELEASE_COMMAND_LOG"]).open("a") as log:
    print(command, file=log)
state = Path(os.environ["RELEASE_STATE"])
failure = os.environ["RELEASE_FAILURE"]
if command == "view":
    sys.exit(0 if state.exists() else 1)
elif command == "create":
    assert "--draft" in sys.argv
    if failure == "create":
        sys.exit(1)
    state.write_text("draft")
elif command == "upload":
    sys.exit(1 if failure == "upload" else 0)
elif command == "delete":
    state.unlink()
else:
    sys.exit(99)
"""
    )
    fake_gh.chmod(0o755)
    result = subprocess.run(
        [native_shell("bash"), "--noprofile", "--norc"],
        input=script,
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
            "GH_REPO": "example/release-test",
            "RELEASE_TAG": "0.3.3" if failure == "wrong-version" else "0.3.2",
            "RELEASE_STATE": str(state),
            "RELEASE_COMMAND_LOG": str(log),
            "RELEASE_FAILURE": failure or "",
        },
        capture_output=True,
        text=True,
        timeout=10,
    )
    commands = log.read_text().splitlines() if log.exists() else []
    if failure is None:
        assert result.returncode == 0, result.stderr
        assert state.read_text() == "draft"
        assert commands == ["view", "create", "upload"]
    else:
        assert result.returncode != 0
        if failure == "existing-release":
            assert state.read_text() == "keep existing release"
            assert commands == ["view"]
        else:
            assert not state.exists()
            if failure == "upload":
                assert commands == ["view", "create", "upload", "delete"]
            elif failure == "create":
                assert commands == ["view", "create"]
            else:
                assert commands == []
