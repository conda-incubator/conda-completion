"""Tests for shell script generation and path quoting."""

from __future__ import annotations

from pathlib import Path

import pytest
import shellingham

from conda_completion.shell import Shell, get_shell_registry


@pytest.mark.parametrize(
    "path_str,expected",
    [
        ("/usr/bin/completer", "'/usr/bin/completer'"),
        ("/path with spaces/bin", "'/path with spaces/bin'"),
        ("/path'quote/bin", "'/path'\\''quote/bin'"),
    ],
    ids=["simple", "spaces", "single-quote"],
)
def test_posix_quote(path_str, expected):
    assert Shell.posix_quote(Path(path_str)) == expected


@pytest.mark.parametrize(
    "path_str,expected",
    [
        ("C:\\Users\\bin\\completer", "'C:\\Users\\bin\\completer'"),
        ("C:\\path with spaces\\bin", "'C:\\path with spaces\\bin'"),
        ("C:\\it''s\\bin", "'C:\\it''''s\\bin'"),
    ],
    ids=["simple", "spaces", "single-quote"],
)
def test_powershell_quote(path_str, expected):
    assert Shell.powershell_quote(Path(path_str)) == expected


@pytest.mark.parametrize(
    "shell_name",
    ["bash", "zsh", "powershell", "fish"],
)
def test_script_generation_does_not_raise(shell_name):
    registry = get_shell_registry()
    if shell_name not in registry:
        pytest.skip(f"{shell_name} not available")

    shell = registry[shell_name]
    script = shell.script(
        Path("/usr/local/bin/_conda_completer"),
        Path("/home/user/.cache/conda/completion/completion.msgpack"),
    )
    assert len(script) > 0
    assert "_conda_completer" in script or "cc_completer" in script


@pytest.mark.parametrize(
    "shell_name",
    ["bash", "zsh", "powershell", "fish"],
)
def test_script_with_special_paths(shell_name):
    registry = get_shell_registry()
    if shell_name not in registry:
        pytest.skip(f"{shell_name} not available")

    shell = registry[shell_name]
    script = shell.script(
        Path("/path with spaces/bin/_conda_completer"),
        Path("/path with spaces/cache/completion.msgpack"),
    )
    assert len(script) > 0


def test_get_shell_registry_includes_tier_1():
    registry = get_shell_registry()
    assert "bash" in registry
    assert "zsh" in registry
    assert "powershell" in registry


def test_get_shell_registry_includes_fish():
    registry = get_shell_registry()
    assert "fish" in registry


@pytest.mark.parametrize(
    "shell_name",
    ["bash", "zsh", "fish", "powershell"],
)
def test_detect_shell_uses_shellingham(monkeypatch, shell_name):
    monkeypatch.setattr(
        shellingham, "detect_shell", lambda: (shell_name, f"/usr/bin/{shell_name}")
    )
    assert Shell.detect_shell() == shell_name


@pytest.mark.parametrize(
    "shell_env,platform,expected",
    [
        ("/usr/bin/zsh", "linux", "zsh"),
        ("/usr/local/bin/fish", "linux", "fish"),
        (None, "linux", "bash"),
        (None, "win32", "powershell"),
    ],
    ids=["zsh-from-env", "fish-basename", "empty-linux", "empty-win32"],
)
def test_detect_shell_fallback(shellingham_fails, monkeypatch, shell_env, platform, expected):
    if shell_env is not None:
        monkeypatch.setenv("SHELL", shell_env)
    else:
        monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr("conda_completion.shell.sys.platform", platform)
    assert Shell.detect_shell() == expected


def test_default_rc_path_existing_file(tmp_path, monkeypatch):
    from conda_completion.shell.bash import BashShell

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".bash_profile").touch()

    shell = BashShell()
    rc = shell.default_rc_path()
    assert rc == tmp_path / ".bash_profile"


def test_default_rc_path_prefers_first_existing(tmp_path, monkeypatch):
    from conda_completion.shell.bash import BashShell

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".bashrc").touch()
    (tmp_path / ".bash_profile").touch()

    shell = BashShell()
    rc = shell.default_rc_path()
    assert rc == tmp_path / ".bashrc"


def test_default_rc_path_fallback_to_first_in_list(tmp_path, monkeypatch):
    from conda_completion.shell.bash import BashShell

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    shell = BashShell()
    rc = shell.default_rc_path()
    assert rc == tmp_path / ".bashrc"


def test_default_rc_path_empty_rc_files(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    shell = Shell()
    rc = shell.default_rc_path()
    assert rc is None


def test_powershell_default_rc_path_non_win(tmp_path, monkeypatch):
    from conda_completion.shell.powershell import PowerShellShell

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr("conda_completion.shell.powershell.sys.platform", "darwin")

    shell = PowerShellShell()
    rc = shell.default_rc_path()
    assert rc is not None
    assert "powershell" in str(rc).lower()


def test_powershell_default_rc_path_existing(tmp_path, monkeypatch):
    from conda_completion.shell.powershell import PowerShellShell

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr("conda_completion.shell.powershell.sys.platform", "darwin")

    profile = tmp_path / ".config" / "powershell" / "Microsoft.PowerShell_profile.ps1"
    profile.parent.mkdir(parents=True)
    profile.touch()

    shell = PowerShellShell()
    rc = shell.default_rc_path()
    assert rc == profile


def test_zsh_script_registers_compdef(tmp_path):
    from conda_completion.shell.zsh import ZshShell

    shell = ZshShell()
    script = shell.script(tmp_path / "_conda_completer", tmp_path / "completion.msgpack")
    assert "compdef _conda conda" in script


def test_powershell_script_contains_register(tmp_path):
    from conda_completion.shell.powershell import PowerShellShell

    shell = PowerShellShell()
    script = shell.script(tmp_path / "_conda_completer", tmp_path / "completion.msgpack")
    assert "Register-ArgumentCompleter" in script
    assert "CompletionResult" in script
    assert str(tmp_path / "_conda_completer") in script
