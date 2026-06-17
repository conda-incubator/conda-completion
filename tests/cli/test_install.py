"""Tests for the install CLI subcommand."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from conda_completion.cli.install import _BLOCK_END, _BLOCK_START, execute_install, source_command
from conda_completion.exceptions import (
    CompleterBinaryNotFoundError,
    ManifestNotFoundError,
    ShellNotSupportedError,
)
from conda_completion.shell import Shell, get_shell_registry


def test_install_block_markers():
    assert "conda-completion" in _BLOCK_START
    assert "conda-completion" in _BLOCK_END


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
        (
            "bash",
            'command -v conda &>/dev/null && eval "$('
            'conda completion init bash --command-name conda)"',
        ),
        (
            "zsh",
            'command -v conda &>/dev/null && eval "$('
            'conda completion init zsh --command-name conda)"',
        ),
        (
            "powershell",
            "if (Get-Command conda -ErrorAction SilentlyContinue)"
            " { conda completion init powershell --command-name conda | Invoke-Expression }",
        ),
        ("fish", "command -q conda; and conda completion init fish --command-name conda | source"),
    ],
    ids=["bash", "zsh", "powershell", "fish"],
)
def test_hook_line_per_shell(shell_name, expected_hook):
    registry = get_shell_registry()
    if shell_name not in registry:
        pytest.skip(f"{shell_name} not available")
    assert registry[shell_name].hook_line() == expected_hook


@pytest.mark.parametrize(
    "shell_name,expected_hook",
    [
        (
            "bash",
            'command -v cx &>/dev/null && eval "$(cx completion init bash --command-name cx)"',
        ),
        (
            "zsh",
            'command -v cx &>/dev/null && eval "$(cx completion init zsh --command-name cx)"',
        ),
        (
            "powershell",
            "if (Get-Command cx -ErrorAction SilentlyContinue)"
            " { cx completion init powershell --command-name cx | Invoke-Expression }",
        ),
        ("fish", "command -q cx; and cx completion init fish --command-name cx | source"),
    ],
    ids=["bash", "zsh", "powershell", "fish"],
)
def test_hook_line_uses_command_name(shell_name, expected_hook):
    registry = get_shell_registry()
    if shell_name not in registry:
        pytest.skip(f"{shell_name} not available")
    assert registry[shell_name].hook_line(command_name="cx") == expected_hook


@pytest.mark.parametrize(
    "shell_name,expected",
    [
        (
            "bash",
            "conda completion --cache-dir 'conda completion cache' init bash",
        ),
        (
            "zsh",
            "conda completion --cache-dir 'conda completion cache' init zsh",
        ),
        (
            "powershell",
            "conda completion --cache-dir 'conda completion cache' init powershell",
        ),
        (
            "fish",
            "conda completion --cache-dir 'conda completion cache' init fish",
        ),
    ],
    ids=["bash", "zsh", "powershell", "fish"],
)
def test_hook_line_preserves_cache_dir(shell_name, expected):
    registry = get_shell_registry()
    if shell_name not in registry:
        pytest.skip(f"{shell_name} not available")
    assert expected in registry[shell_name].hook_line(Path("conda completion cache"))


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


def test_execute_install_appends_to_existing_rc_without_block(
    tmp_path, monkeypatch, stub_generate
):
    rc_file = tmp_path / ".bashrc"
    rc_file.write_text("# existing content\n", encoding="utf-8")
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
    assert content.startswith("# existing content\n")
    assert content.count(_BLOCK_START) == 1


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


def test_execute_install_passes_no_repodata_flag(tmp_path, monkeypatch, stub_generate):
    rc_file = tmp_path / ".bashrc"
    monkeypatch.setattr("conda_completion.cli.install.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )

    args = argparse.Namespace(
        shell=None,
        yes=True,
        dry_run=False,
        no_repodata=True,
    )
    result = execute_install(args)

    assert result == 0
    assert len(stub_generate) == 1
    assert stub_generate[0].no_repodata is True


def test_execute_install_preserves_cache_dir_in_hook(tmp_path, monkeypatch, stub_generate):
    rc_file = tmp_path / ".bashrc"
    cache_dir = tmp_path / "completion-cache"
    monkeypatch.setattr("conda_completion.cli.install.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )

    args = argparse.Namespace(
        shell=None,
        yes=True,
        dry_run=False,
        no_repodata=False,
        cache_dir=cache_dir,
    )
    result = execute_install(args)

    assert result == 0
    assert f"conda completion --cache-dir '{cache_dir.as_posix()}' init bash" in rc_file.read_text(
        encoding="utf-8"
    )


def test_execute_install_preserves_command_name_in_hook(tmp_path, monkeypatch, stub_generate):
    rc_file = tmp_path / ".bashrc"
    monkeypatch.setattr("conda_completion.cli.install.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )

    args = argparse.Namespace(
        shell=None,
        yes=True,
        dry_run=False,
        no_repodata=False,
        command_name="cx",
    )
    result = execute_install(args)

    assert result == 0
    assert "cx completion init bash --command-name cx" in rc_file.read_text(encoding="utf-8")


def test_execute_install_fish_writes_static_completion_script(
    tmp_path, monkeypatch, stub_generate
):
    rc_file = tmp_path / "fish" / "completions" / "conda.fish"
    manifest = tmp_path / "completion.msgpack"
    manifest.write_bytes(b"\x81\xa7version\x01")
    binary = tmp_path / "_conda_completer"
    binary.touch()
    monkeypatch.setattr("conda_completion.shell.fish.FishShell.rc_path", lambda self, _: rc_file)
    monkeypatch.setattr("conda_completion.shell.fish.manifest_path", lambda: manifest)
    monkeypatch.setattr("conda_completion.shell.fish.find_completer_binary", lambda: binary)

    args = argparse.Namespace(
        shell="fish",
        yes=True,
        dry_run=False,
        no_repodata=False,
    )
    result = execute_install(args)

    assert result == 0
    assert len(stub_generate) == 1
    content = rc_file.read_text(encoding="utf-8")
    assert content.count(_BLOCK_START) == 1
    assert "__conda_complete" in content
    assert binary.as_posix() in content
    assert manifest.as_posix() in content
    assert "conda completion init fish" not in content


def test_execute_install_fish_replaces_existing_completion_block(
    tmp_path,
    monkeypatch,
    stub_generate,
):
    rc_file = tmp_path / "fish" / "completions" / "conda.fish"
    rc_file.parent.mkdir(parents=True)
    rc_file.write_text(
        f"# before\n{_BLOCK_START}\n"
        "command -q conda; and conda completion init fish --command-name conda | source\n"
        f"{_BLOCK_END}\n# after\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "completion.msgpack"
    manifest.write_bytes(b"\x81\xa7version\x01")
    binary = tmp_path / "_conda_completer"
    binary.touch()
    monkeypatch.setattr("conda_completion.shell.fish.FishShell.rc_path", lambda self, _: rc_file)
    monkeypatch.setattr("conda_completion.shell.fish.manifest_path", lambda: manifest)
    monkeypatch.setattr("conda_completion.shell.fish.find_completer_binary", lambda: binary)

    args = argparse.Namespace(
        shell="fish",
        yes=True,
        dry_run=False,
        no_repodata=False,
    )
    result = execute_install(args)

    assert result == 0
    assert len(stub_generate) == 1
    content = rc_file.read_text(encoding="utf-8")
    assert content.count(_BLOCK_START) == 1
    assert "# before" in content
    assert "# after" in content
    assert "__conda_complete" in content
    assert "conda completion init fish" not in content


def test_execute_install_fish_dry_run_does_not_generate(tmp_path, monkeypatch, stub_generate):
    rc_file = tmp_path / "fish" / "completions" / "conda.fish"
    monkeypatch.setattr("conda_completion.shell.fish.FishShell.rc_path", lambda self, _: rc_file)

    args = argparse.Namespace(
        shell="fish",
        yes=False,
        dry_run=True,
        no_repodata=False,
    )
    result = execute_install(args)

    assert result == 0
    assert stub_generate == []
    assert not rc_file.exists()


@pytest.mark.parametrize(
    "manifest_exists,missing_completer,expected_error",
    [
        (False, False, ManifestNotFoundError),
        (True, True, CompleterBinaryNotFoundError),
    ],
    ids=["missing-manifest", "missing-completer"],
)
def test_execute_install_fish_static_install_errors(
    tmp_path,
    monkeypatch,
    stub_generate,
    manifest_exists,
    missing_completer,
    expected_error,
):
    rc_file = tmp_path / "fish" / "completions" / "conda.fish"
    manifest = tmp_path / "completion.msgpack"
    binary = tmp_path / "_conda_completer"
    binary.touch()
    if manifest_exists:
        manifest.write_bytes(b"\x81\xa7version\x01")
    monkeypatch.setattr("conda_completion.shell.fish.FishShell.rc_path", lambda self, _: rc_file)
    monkeypatch.setattr("conda_completion.shell.fish.manifest_path", lambda: manifest)

    if missing_completer:

        def find_completer_binary():
            raise FileNotFoundError
    else:

        def find_completer_binary():
            return binary

    monkeypatch.setattr(
        "conda_completion.shell.fish.find_completer_binary",
        find_completer_binary,
    )

    args = argparse.Namespace(
        shell="fish",
        yes=True,
        dry_run=False,
        no_repodata=False,
    )
    with pytest.raises(expected_error):
        execute_install(args)

    assert len(stub_generate) == 1
    assert not rc_file.exists()


def test_execute_install_reads_command_name_from_env(tmp_path, monkeypatch, stub_generate):
    rc_file = tmp_path / ".bashrc"
    monkeypatch.setattr("conda_completion.cli.install.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )
    monkeypatch.setenv("CONDA_COMPLETION_COMMAND_NAME", "cx")

    args = argparse.Namespace(
        shell=None,
        yes=True,
        dry_run=False,
        no_repodata=False,
    )
    result = execute_install(args)

    assert result == 0
    assert "cx completion init bash --command-name cx" in rc_file.read_text(encoding="utf-8")


def test_source_command_for_powershell():
    assert source_command("powershell", "ignored") == ". $PROFILE"


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


def test_execute_install_prompt_accepted(tmp_path, monkeypatch, stub_generate):
    rc_file = tmp_path / ".bashrc"
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )
    monkeypatch.setattr("builtins.input", lambda _: "yes")

    args = argparse.Namespace(shell="bash", yes=False, dry_run=False)
    result = execute_install(args)

    assert result == 0
    assert len(stub_generate) == 1
    assert _BLOCK_START in rc_file.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "which_result,expected_message,expected_command",
    [
        (None, "conda is not on PATH", "conda"),
        ("/usr/bin/conda", None, "conda"),
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
    expected_command,
):
    rc_file = tmp_path / ".bashrc"
    monkeypatch.setattr("conda_completion.cli.install.Shell.detect_shell", lambda: "bash")
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )
    which_calls = []

    def fake_which(command):
        which_calls.append(command)
        return which_result

    monkeypatch.setattr("conda_completion.cli.install.shutil.which", fake_which)

    args = argparse.Namespace(shell=None, yes=True, dry_run=False)
    result = execute_install(args)
    assert result == 0
    captured = capsys.readouterr()
    if expected_message is None:
        assert "conda is not on PATH" not in captured.out
    else:
        assert expected_message in captured.out
    assert which_calls == [expected_command]


def test_install_custom_command_path_warning(tmp_path, monkeypatch, capsys, stub_generate):
    rc_file = tmp_path / ".bashrc"
    monkeypatch.setattr(
        "conda_completion.shell.bash.BashShell.default_rc_path",
        lambda self: rc_file,
    )
    monkeypatch.setattr("conda_completion.cli.install.shutil.which", lambda _: None)

    args = argparse.Namespace(
        shell="bash",
        yes=True,
        dry_run=False,
        no_repodata=False,
        command_name="cx",
    )
    result = execute_install(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "cx is not on PATH" in captured.out
    assert "Add cx to your PATH" in captured.out
