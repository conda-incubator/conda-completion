"""Tests for shell script generation and path quoting."""

from __future__ import annotations

from pathlib import Path

import pytest

from conda_completion.shell import Shell, get_shell_registry
from conda_completion.shell.bash import BashShell
from conda_completion.shell.powershell import PowerShellShell
from conda_completion.shell.zsh import ZshShell


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


def test_get_shell_registry_includes_supported_shells():
    registry = get_shell_registry()
    assert "bash" in registry
    assert "zsh" in registry
    assert "powershell" in registry
    assert "fish" in registry


@pytest.mark.parametrize(
    "shell_env,expected",
    [
        ("/usr/bin/zsh", "zsh"),
        ("/usr/local/bin/fish", "fish"),
        ("/bin/bash", "bash"),
    ],
    ids=["zsh", "fish", "bash"],
)
def test_detect_shell_from_env(monkeypatch, shell_env, expected):
    monkeypatch.delenv("CONDA_COMPLETION_SHELL", raising=False)
    monkeypatch.setattr(Shell, "detect_parent_shell", staticmethod(lambda: None))
    monkeypatch.setenv("SHELL", shell_env)
    assert Shell.detect_shell() == expected


@pytest.mark.parametrize(
    "platform,expected",
    [
        ("linux", "bash"),
        ("win32", "powershell"),
    ],
    ids=["linux-fallback", "win32-fallback"],
)
def test_detect_shell_empty_env(monkeypatch, platform, expected):
    monkeypatch.delenv("CONDA_COMPLETION_SHELL", raising=False)
    monkeypatch.setattr(Shell, "detect_parent_shell", staticmethod(lambda: None))
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr("conda_completion.shell.sys.platform", platform)
    assert Shell.detect_shell() == expected


@pytest.mark.parametrize(
    "override,expected",
    [
        ("fish", "fish"),
        ("/usr/local/bin/fish", "fish"),
        ("pwsh", "powershell"),
        ("/usr/local/bin/pwsh.exe", "powershell"),
        ("zsh", "zsh"),
    ],
    ids=["bare-name", "full-path", "pwsh", "pwsh-exe-path", "zsh"],
)
def test_detect_shell_conda_completion_shell_override(monkeypatch, override, expected):
    monkeypatch.setenv("CONDA_COMPLETION_SHELL", override)
    monkeypatch.setenv("SHELL", "/bin/bash")
    assert Shell.detect_shell() == expected


def test_detect_shell_override_takes_priority(monkeypatch):
    monkeypatch.setenv("CONDA_COMPLETION_SHELL", "fish")
    monkeypatch.setenv("SHELL", "/bin/zsh")
    assert Shell.detect_shell() == "fish"


@pytest.mark.parametrize(
    "parent_comm,expected",
    [
        ("/usr/bin/fish", "fish"),
        ("-zsh", "zsh"),
        ("pwsh", "powershell"),
        ("pwsh.exe", "powershell"),
        ("powershell.exe", "powershell"),
        ("cmd", None),
        ("cmd.exe", None),
    ],
    ids=[
        "fish-path",
        "login-zsh",
        "pwsh",
        "pwsh-exe",
        "powershell-exe",
        "cmd-unsupported",
        "cmd-exe-unsupported",
    ],
)
def test_detect_parent_shell_parses_process_tree(monkeypatch, parent_comm, expected):
    ps_output = f"""
      1     0 launchd
      123   1 {parent_comm}
      456 123 python
    """

    monkeypatch.setattr("conda_completion.shell.os.getpid", lambda: 456)
    monkeypatch.setattr(
        "conda_completion.shell.subprocess.check_output",
        lambda *args, **kwargs: ps_output,
    )

    assert Shell.detect_parent_shell() == expected


def test_detect_shell_process_tree_beats_shell_env(monkeypatch):
    monkeypatch.delenv("CONDA_COMPLETION_SHELL", raising=False)
    monkeypatch.setattr(Shell, "detect_parent_shell", staticmethod(lambda: "fish"))
    monkeypatch.setenv("SHELL", "/bin/bash")
    assert Shell.detect_shell() == "fish"


def test_detect_shell_falls_through_when_process_tree_fails(monkeypatch):
    monkeypatch.delenv("CONDA_COMPLETION_SHELL", raising=False)
    monkeypatch.setattr(Shell, "detect_parent_shell", staticmethod(lambda: None))
    monkeypatch.setenv("SHELL", "/bin/bash")
    assert Shell.detect_shell() == "bash"


def test_default_rc_path_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".bash_profile").touch()

    shell = BashShell()
    rc = shell.default_rc_path()
    assert rc == tmp_path / ".bash_profile"


def test_default_rc_path_prefers_first_existing(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".bashrc").touch()
    (tmp_path / ".bash_profile").touch()

    shell = BashShell()
    rc = shell.default_rc_path()
    assert rc == tmp_path / ".bashrc"


def test_default_rc_path_fallback_to_first_in_list(tmp_path, monkeypatch):
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
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr("conda_completion.shell.powershell.sys.platform", "darwin")

    shell = PowerShellShell()
    rc = shell.default_rc_path()
    assert rc is not None
    assert "powershell" in str(rc).lower()


def test_powershell_default_rc_path_win32(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.setattr("conda_completion.shell.powershell.sys.platform", "win32")
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "profile"))

    shell = PowerShellShell()
    rc = shell.default_rc_path()

    assert (
        rc
        == tmp_path / "profile" / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
    )


def test_powershell_default_rc_path_existing(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr("conda_completion.shell.powershell.sys.platform", "darwin")

    profile = tmp_path / ".config" / "powershell" / "Microsoft.PowerShell_profile.ps1"
    profile.parent.mkdir(parents=True)
    profile.touch()

    shell = PowerShellShell()
    rc = shell.default_rc_path()
    assert rc == profile


def test_zsh_script_registers_compdef(tmp_path):
    shell = ZshShell()
    script = shell.script(tmp_path / "_conda_completer", tmp_path / "completion.msgpack")
    assert "compdef _conda conda" in script


def test_powershell_script_contains_register(tmp_path):
    shell = PowerShellShell()
    script = shell.script(tmp_path / "_conda_completer", tmp_path / "completion.msgpack")
    assert "Register-ArgumentCompleter" in script
    assert "CompletionResult" in script
    assert str(tmp_path / "_conda_completer") in script
    assert "CommandElements" in script
    assert ".ToString().Split()" not in script
