"""Exercise generated scripts through native shell parsing and completion."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conda_completion.cli.init import execute_init
from conda_completion.paths import set_cache_dir_override
from conda_completion.shell import Shell
from conda_completion.shell.bash import BashShell
from conda_completion.shell.fish import FishShell
from conda_completion.shell.powershell import PowerShellShell


@pytest.mark.parametrize(
    "candidate",
    ["dev --json -y", "dev  env", r"dev\path", r"dev\\path", "dev~env", "dév --json -y"],
)
@pytest.mark.parametrize("command", ["conda install", "cinstall"])
def test_bash_completion_preserves_argument(
    tmp_path, completion_runtime, bash_complete, monkeypatch, candidate, command
):
    monkeypatch.setenv("LC_ALL", "C")
    binary, manifest = completion_runtime
    (tmp_path / "environment.yml").write_text(f"name: {json.dumps(candidate)}\n")
    script = BashShell().script(binary, manifest)

    assert bash_complete(script, f"{command} --name d\t") == ["install", "--name", candidate]


@pytest.mark.parametrize("prefix", ["d", "'d", '"d', "'d'", '"d"'])
def test_bash_filename_fallback(tmp_path, completion_runtime, bash_complete, prefix):
    binary, manifest = completion_runtime
    candidate = r"dev\ env"
    (tmp_path / candidate).touch()

    assert bash_complete(
        BashShell().script(binary, manifest), f"conda install --name {prefix}\t"
    ) == [
        "install",
        "--name",
        candidate,
    ]


@pytest.mark.parametrize(
    "prefix,closing",
    [("'d", "'"), ('"d', '"'), ("'d'", ""), ('"d"', ""), ("d'", "'"), ('d"', '"')],
)
def test_bash_withholds_quoted_project_candidates(
    tmp_path, completion_runtime, bash_complete, prefix, closing
):
    binary, manifest = completion_runtime
    candidate = prefix + "ev --json -y"
    (tmp_path / "environment.yml").write_text(f"name: {json.dumps(candidate)}\n")

    assert bash_complete(
        BashShell().script(binary, manifest), f"conda install --name {prefix}\t{closing}"
    ) == ["install", "--name", "d"]


def test_bash_completion_does_not_append_directory_slash(
    tmp_path, completion_runtime, bash_complete
):
    binary, manifest = completion_runtime
    candidate = "dev env"
    (tmp_path / candidate).mkdir()
    (tmp_path / "environment.yml").write_text(f"name: {json.dumps(candidate)}\n")

    assert bash_complete(BashShell().script(binary, manifest), "conda install --name d\t") == [
        "install",
        "--name",
        candidate,
    ]


@pytest.mark.parametrize(
    "line,expected",
    [
        ("conda ins\t--dry-r\t", ["install", "--dry-run"]),
        ("conda install nump\t", ["install", "numpy"]),
    ],
)
def test_bash_completion_continues(completion_runtime, bash_complete, line, expected):
    assert bash_complete(BashShell().script(*completion_runtime), line) == expected


@pytest.mark.parametrize(
    "candidate",
    ["dev --json -y", "dev  env", r"dev\path", r"dev\\path", "@dev", "~dev"],
)
@pytest.mark.parametrize("prefix_quote", ["", "'", '"'])
def test_powershell_completion_preserves_argument(
    tmp_path, completion_runtime, native_shell, candidate, prefix_quote
):
    binary, manifest = completion_runtime
    (tmp_path / "environment.yml").write_text(f"name: {json.dumps(candidate)}\n")
    recorder = tmp_path / "record.py"
    recorder.write_text("import json, sys\nprint(json.dumps(sys.argv[1:]))\n")
    command = Path(sys.executable).name
    script = PowerShellShell().script(binary, manifest, command)
    prefix = candidate[:2] if candidate.startswith("~") else candidate[:1]
    line = f"{command} {Shell.powershell_quote(recorder)} install --name {prefix_quote}{prefix}"
    script += (
        f"\n$line = {Shell.powershell_quote(line)}\n"
        """
$result = TabExpansion2 $line $line.Length
if ($result.CompletionMatches.Count -ne 1) { throw 'Expected one completion' }
$match = $result.CompletionMatches[0]
$completed = $line.Remove($result.ReplacementIndex, $result.ReplacementLength)
$completed = $completed.Insert($result.ReplacementIndex, $match.CompletionText)
& ([scriptblock]::Create($completed))
"""
    )
    result = subprocess.run(
        [native_shell("pwsh"), "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=tmp_path,
        env={**os.environ, "HOME": str(tmp_path), "USERPROFILE": str(tmp_path)},
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ["install", "--name", candidate]


@pytest.mark.parametrize(
    "suffix,completion,expected",
    [
        (" --name ", "demo", ["install", "--name", "demo"]),
        (" --dry-r", "--dry-run", ["install", "--dry-run"]),
    ],
)
def test_powershell_completion_continues(
    tmp_path, completion_runtime, native_shell, suffix, completion, expected
):
    binary, manifest = completion_runtime
    (tmp_path / "environment.yml").write_text("name: demo\n")
    recorder = tmp_path / "record.py"
    recorder.write_text("import json, sys\nprint(json.dumps(sys.argv[1:]))\n")
    command = Path(sys.executable).name
    line = f"{command} {Shell.powershell_quote(recorder)} ins"
    script = PowerShellShell().script(binary, manifest, command)
    script += """
function Complete-Line($line, $expected) {
    $result = TabExpansion2 $line $line.Length
    $match = $result.CompletionMatches | Where-Object ListItemText -EQ $expected
    if (-not $match) { throw 'Expected completion is missing' }
    $completed = $line.Remove($result.ReplacementIndex, $result.ReplacementLength)
    return $completed.Insert($result.ReplacementIndex, $match.CompletionText)
}
"""
    script += f"$line = Complete-Line {Shell.powershell_quote(line)} 'install'\n"
    script += (
        f"$line = Complete-Line ($line + {Shell.powershell_quote(suffix)})"
        f" {Shell.powershell_quote(completion)}\n"
    )
    script += "& ([scriptblock]::Create($line))\n"
    result = subprocess.run(
        [native_shell("pwsh"), "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == expected


@pytest.mark.parametrize(
    "value", ["cache with spaces", r"cache\\path", "cache'path", "cache\\'(printf INJECTED) #"]
)
@pytest.mark.parametrize("mode", ["script", "init", "install", "hook"])
def test_fish_script_preserves_paths(tmp_path, native_shell, monkeypatch, capsys, value, mode):
    if sys.platform == "win32":
        pytest.skip("Fish path characters require a Unix filesystem")
    directory = tmp_path / value
    directory.mkdir()
    binary = directory / "completer"
    binary.write_text("#!/bin/sh\nexit 0\n")
    binary.chmod(0o700)
    manifest = directory / "completion.msgpack"
    manifest.touch()
    cache_link = tmp_path / "cache-link"
    cache_link.symlink_to(directory, target_is_directory=True)
    monkeypatch.setattr("conda_completion.paths._cache_dir_override", None)
    set_cache_dir_override(cache_link)
    monkeypatch.setattr("conda_completion.cli.init.find_completer_binary", lambda: binary)
    monkeypatch.setattr("conda_completion.shell.fish.find_completer_binary", lambda: binary)
    if mode == "init":
        execute_init(argparse.Namespace(shell="fish"))
        script = capsys.readouterr().out
    elif mode == "install":
        script = FishShell().install_body()
    elif mode == "hook":
        script = (
            "function conda\n"
            "printf 'set -g captured_cache %s\\n' (string escape -- $argv[3])\n"
            "end\n" + FishShell().hook_line(directory)
        )
    else:
        script = FishShell().script(binary, manifest)
    if mode == "hook":
        script += "\nprintf '%s\\n' $captured_cache\n"
        expected = [str(directory)]
    else:
        script += "\nprintf '%s\\n' $__conda_completion_completer $__conda_completion_manifest\n"
        expected = [str(binary), str(manifest)]
    result = subprocess.run(
        [native_shell("fish"), "--no-config", "-c", script],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == expected
