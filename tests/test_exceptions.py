"""Tests for custom exception classes."""

from __future__ import annotations

from conda_completion.exceptions import (
    CompleterBinaryNotFoundError,
    CondaCompletionError,
    ManifestError,
    ManifestNotFoundError,
    ShellNotSupportedError,
)


def test_manifest_not_found_error():
    exc = ManifestNotFoundError()
    assert "not found" in exc.error_message.lower()
    assert len(exc.hints) > 0
    assert "generate" in exc.hints[0].lower()


def test_manifest_error():
    exc = ManifestError("bad format")
    assert "bad format" in exc.error_message
    assert len(exc.hints) > 0


def test_completer_binary_not_found_error():
    exc = CompleterBinaryNotFoundError()
    assert "not found" in exc.error_message.lower()
    assert len(exc.hints) > 0


def test_shell_not_supported_error():
    exc = ShellNotSupportedError("nushell", ["bash", "zsh"])
    assert "nushell" in exc.error_message
    assert any("bash" in h for h in exc.hints)


def test_all_inherit_from_base():
    assert issubclass(ManifestNotFoundError, CondaCompletionError)
    assert issubclass(ManifestError, CondaCompletionError)
    assert issubclass(CompleterBinaryNotFoundError, CondaCompletionError)
    assert issubclass(ShellNotSupportedError, CondaCompletionError)
