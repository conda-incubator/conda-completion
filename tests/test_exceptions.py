"""Tests for custom exception classes."""

from __future__ import annotations

import pytest

from conda_completion.exceptions import (
    CompleterBinaryNotFoundError,
    CondaCompletionError,
    IntrospectionError,
    ManifestError,
    ManifestNotFoundError,
    ShellNotSupportedError,
)


@pytest.mark.parametrize(
    "exc,substring",
    [
        (ManifestNotFoundError(), "not found"),
        (ManifestError("bad format"), "bad format"),
        (IntrospectionError("plugin panic"), "plugin panic"),
        (CompleterBinaryNotFoundError(), "not found"),
        (ShellNotSupportedError("nushell", ["bash", "zsh"]), "nushell"),
    ],
    ids=[
        "manifest-not-found",
        "manifest-error",
        "introspection-error",
        "binary-not-found",
        "shell-not-supported",
    ],
)
def test_error_message_content(exc, substring):
    assert substring in exc.error_message.lower()
    assert len(exc.hints) > 0


def test_shell_not_supported_lists_supported_shells():
    exc = ShellNotSupportedError("nushell", ["bash", "zsh"])
    assert any("bash" in h for h in exc.hints)


@pytest.mark.parametrize(
    "cls",
    [
        ManifestNotFoundError,
        ManifestError,
        IntrospectionError,
        CompleterBinaryNotFoundError,
        ShellNotSupportedError,
    ],
)
def test_all_inherit_from_base(cls):
    assert issubclass(cls, CondaCompletionError)
