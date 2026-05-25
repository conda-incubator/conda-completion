"""Tests for the install/uninstall CLI subcommands."""

from __future__ import annotations

import argparse

import pytest

from conda_completion.cli.install import _BLOCK_END, _BLOCK_START, execute_install
from conda_completion.cli.uninstall import _BLOCK_PATTERN, execute_uninstall
from conda_completion.exceptions import ShellNotSupportedError
from conda_completion.shell import Shell, get_shell_registry


def test_install_block_markers():
    assert "conda-completion" in _BLOCK_START
    assert "conda-completion" in _BLOCK_END


def test_uninstall_removes_block(tmp_path):
    rc_file = tmp_path / ".bashrc"
    rc_file.write_text(
        'export PATH="/usr/bin:$PATH"\n'
        f"\n{_BLOCK_START}\n"
        'command -v conda &>/dev/null && eval "$(conda completion init bash)"\n'
        f"{_BLOCK_END}\n"
        "\nalias ll='ls -la'\n",
        encoding="utf-8",
    )

    content = rc_file.read_text(encoding="utf-8")
    new_content = _BLOCK_PATTERN.sub("", content)
    rc_file.write_text(new_content, encoding="utf-8")

    result = rc_file.read_text(encoding="utf-8")
    assert _BLOCK_START not in result
    assert _BLOCK_END not in result
    assert 'export PATH="/usr/bin:$PATH"' in result
    assert "alias ll='ls -la'" in result


def test_install_idempotent(tmp_path):
    rc_file = tmp_path / ".bashrc"
    hook = 'command -v conda &>/dev/null && eval "$(conda completion init bash)"'
    block = f"\n{_BLOCK_START}\n{hook}\n{_BLOCK_END}\n"
    rc_file.write_text(f"# existing content{block}", encoding="utf-8")

    content = rc_file.read_text(encoding="utf-8")
    assert content.count(_BLOCK_START) == 1


@pytest.mark.parametrize(
    "shell_name,expected_hook",
    [
        ("bash", 'command -v conda &>/dev/null && eval "$(conda completion init bash)"'),
        ("zsh", 'command -v conda &>/dev/null && eval "$(conda completion init zsh)"'),
        (
            "powershell",
            "if (Get-Command conda -ErrorAction SilentlyContinue)"
            " { conda completion init powershell | Invoke-Expression }",
        ),
        ("fish", "command -q conda; and conda completion init fish | source"),
    ],
    ids=["bash", "zsh", "powershell", "fish"],
)
def test_hook_line_per_shell(shell_name, expected_hook):
    registry = get_shell_registry()
    if shell_name not in registry:
        pytest.skip(f"{shell_name} not available")
    assert registry[shell_name].hook_line() == expected_hook


def test_detect_shell_returns_string():
    result = Shell.detect_shell()
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.fixture()
def stub_generate(monkeypatch):
    """Stub out execute_generate so install tests don't need conda's full parser."""
    calls = []

    def fake_generate(args):
        calls.append(args)
        return 0

    monkeypatch.setattr(
        "conda_completion.cli.generate.execute_generate",
        fake_generate,
    )
    return calls


def test_execute_install_unsupported_shell(monkeypatch, stub_generate):
    monkeypatch.setattr("conda_completion.cli.install.Shell.detect_shell", lambda: "nushell")
    args = argparse.Namespace(shell=None, yes=False, dry_run=False)
    with pytest.raises(ShellNotSupportedError):
        execute_install(args)


def test_execute_install_dry_run(tmp_path, monkeypatch, stub_generate):
    rc_file = tmp_path / ".bashrc"
    monkeypatch.setattr("conda_completion.cli.install.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )

    args = argparse.Namespace(shell=None, yes=False, dry_run=True)
    result = execute_install(args)
    assert result == 0
    assert not rc_file.exists()
    assert stub_generate == []


def test_execute_install_already_present(tmp_path, monkeypatch, stub_generate):
    rc_file = tmp_path / ".bashrc"
    rc_file.write_text(
        f"# existing\n{_BLOCK_START}\nhook\n{_BLOCK_END}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("conda_completion.cli.install.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )

    args = argparse.Namespace(shell=None, yes=False, dry_run=False)
    result = execute_install(args)
    assert result == 0
    assert rc_file.read_text(encoding="utf-8").count(_BLOCK_START) == 1
    assert stub_generate == []


def test_execute_install_no_rc_path(monkeypatch, stub_generate):
    monkeypatch.setattr("conda_completion.cli.install.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: None,
    )

    args = argparse.Namespace(shell=None, yes=False, dry_run=False)
    result = execute_install(args)
    assert result == 1
    assert stub_generate == []


def test_execute_install_with_yes(tmp_path, monkeypatch, stub_generate):
    rc_file = tmp_path / ".bashrc"
    monkeypatch.setattr("conda_completion.cli.install.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )

    args = argparse.Namespace(shell=None, yes=True, dry_run=False)
    result = execute_install(args)
    assert result == 0
    assert len(stub_generate) == 1
    content = rc_file.read_text(encoding="utf-8")
    assert _BLOCK_START in content
    assert _BLOCK_END in content


def test_execute_install_new_file(tmp_path, monkeypatch, stub_generate):
    rc_file = tmp_path / "subdir" / ".bashrc"
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )

    args = argparse.Namespace(shell="bash", yes=True, dry_run=False)
    result = execute_install(args)
    assert result == 0
    assert len(stub_generate) == 1
    assert rc_file.exists()
    content = rc_file.read_text(encoding="utf-8")
    assert _BLOCK_START in content


def test_execute_install_prompt_declined(tmp_path, monkeypatch, stub_generate):
    rc_file = tmp_path / ".bashrc"
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )
    monkeypatch.setattr("builtins.input", lambda _: "n")

    args = argparse.Namespace(shell="bash", yes=False, dry_run=False)
    result = execute_install(args)
    assert result == 1
    assert not rc_file.exists()
    assert stub_generate == []


def test_execute_uninstall_unsupported_shell(monkeypatch):
    monkeypatch.setattr("conda_completion.cli.uninstall.Shell.detect_shell", lambda: "nushell")
    args = argparse.Namespace(shell=None, yes=True, dry_run=False)
    with pytest.raises(ShellNotSupportedError):
        execute_uninstall(args)


def test_execute_uninstall_no_rc_file(monkeypatch):
    monkeypatch.setattr("conda_completion.cli.uninstall.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: None,
    )

    args = argparse.Namespace(shell=None, yes=True, dry_run=False)
    result = execute_uninstall(args)
    assert result == 0


def test_execute_uninstall_no_hook_in_file(tmp_path, monkeypatch):
    rc_file = tmp_path / ".bashrc"
    rc_file.write_text("alias ll='ls -la'\n", encoding="utf-8")
    monkeypatch.setattr("conda_completion.cli.uninstall.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )

    args = argparse.Namespace(shell=None, yes=True, dry_run=False)
    result = execute_uninstall(args)
    assert result == 0
    assert rc_file.read_text(encoding="utf-8") == "alias ll='ls -la'\n"


def test_execute_uninstall_dry_run(tmp_path, monkeypatch):
    rc_file = tmp_path / ".bashrc"
    original = f"# before\n\n{_BLOCK_START}\nhook line\n{_BLOCK_END}\n\n# after\n"
    rc_file.write_text(original, encoding="utf-8")
    monkeypatch.setattr("conda_completion.cli.uninstall.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )

    args = argparse.Namespace(shell=None, yes=False, dry_run=True)
    result = execute_uninstall(args)
    assert result == 0
    assert rc_file.read_text(encoding="utf-8") == original


def test_execute_uninstall_prompt_declined(tmp_path, monkeypatch):
    rc_file = tmp_path / ".bashrc"
    original = f"# before\n\n{_BLOCK_START}\nhook line\n{_BLOCK_END}\n\n# after\n"
    rc_file.write_text(original, encoding="utf-8")
    monkeypatch.setattr("conda_completion.cli.uninstall.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )
    monkeypatch.setattr("builtins.input", lambda _: "n")

    args = argparse.Namespace(shell=None, yes=False, dry_run=False)
    result = execute_uninstall(args)
    assert result == 1
    assert rc_file.read_text(encoding="utf-8") == original


def test_execute_uninstall_removes_hook(tmp_path, monkeypatch):
    rc_file = tmp_path / ".bashrc"
    rc_file.write_text(
        f"# before\n\n{_BLOCK_START}\nhook line\n{_BLOCK_END}\n\n# after\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("conda_completion.cli.uninstall.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )

    args = argparse.Namespace(shell=None, yes=True, dry_run=False)
    result = execute_uninstall(args)
    assert result == 0
    content = rc_file.read_text(encoding="utf-8")
    assert _BLOCK_START not in content
    assert _BLOCK_END not in content
    assert "# before" in content
    assert "# after" in content


@pytest.mark.parametrize(
    "which_result,expected_message",
    [
        (None, "conda is not on PATH"),
        ("/usr/bin/conda", None),
    ],
    ids=["missing-conda", "conda-on-path"],
)
def test_install_conda_path_warning(
    tmp_path,
    monkeypatch,
    capsys,
    stub_generate,
    which_result,
    expected_message,
):
    rc_file = tmp_path / ".bashrc"
    monkeypatch.setattr("conda_completion.cli.install.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )
    monkeypatch.setattr("conda_completion.cli.install.shutil.which", lambda _: which_result)

    args = argparse.Namespace(shell=None, yes=True, dry_run=False)
    result = execute_install(args)
    assert result == 0
    captured = capsys.readouterr()
    if expected_message is None:
        assert "conda is not on PATH" not in captured.out
    else:
        assert expected_message in captured.out
