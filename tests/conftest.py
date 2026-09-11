"""Root test configuration for conda-completion."""

from __future__ import annotations

import os
import re
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path

import msgpack
import pytest


@pytest.fixture
def native_shell():
    def resolve(name):
        binary = shutil.which(name)
        if binary is None:
            pytest.skip(f"{name} is not installed")
        return binary

    return resolve


@pytest.fixture
def completion_runtime(tmp_path):
    binary = (
        Path(__file__).parent.parent
        / "target"
        / "release"
        / ("_conda_completer.exe" if sys.platform == "win32" else "_conda_completer")
    )
    if not binary.is_file():
        pytest.skip("completer binary not built")
    manifest = tmp_path / "completion.msgpack"
    manifest.write_bytes(
        msgpack.packb(
            {
                "version": 1,
                "commands": {
                    "install": {
                        "options": {
                            "--name": {"completion_type": "env_name"},
                            "--dry-run": {},
                        },
                        "positionals": [{"name": "packages", "completion_type": "package_spec"}],
                    }
                },
                "package_names": ["numpy"],
                "aliases": {"cinstall": {"target": ["install"]}},
            }
        )
    )
    return binary, manifest


@pytest.fixture
def bash_complete(tmp_path, native_shell):
    if sys.platform == "win32":
        pytest.skip("Bash Readline tests require a Unix terminal")
    pty = pytest.importorskip("pty")
    bash = native_shell("bash")
    supports_mapfile = subprocess.run([bash, "-c", "type mapfile"], capture_output=True)
    if supports_mapfile.returncode:
        pytest.skip("Bash with mapfile is required")

    def run(script, line):
        rc = tmp_path / "bashrc"
        rc.write_text(
            "conda() { printf '\\036%s\\037' \"$@\"; printf '\\n__DONE__\\n'; }\n"
            'cinstall() { conda install "$@"; }\n' + script + "\nPS1='__READY__ '\n"
            "bind 'set enable-bracketed-paste off'\n",
            encoding="utf-8",
        )
        master, slave = pty.openpty()
        process = subprocess.Popen(
            [bash, "--noprofile", "--rcfile", str(rc), "-i"],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            cwd=tmp_path,
            env={**os.environ, "HISTFILE": os.devnull, "HOME": str(tmp_path)},
            start_new_session=True,
        )
        os.close(slave)

        def read_until(marker):
            data = b""
            deadline = time.monotonic() + 10
            while marker not in data and time.monotonic() < deadline:
                if select.select([master], [], [], 0.1)[0]:
                    data += os.read(master, 65536)
            assert marker in data, data.decode(errors="replace")
            return data

        try:
            read_until(b"__READY__")
            os.write(master, (line + "\n").encode())
            output = read_until(b"__DONE__")
            return [arg.decode() for arg in re.findall(rb"\x1e([^\x1f]*)\x1f", output)]
        finally:
            process.kill()
            process.wait(timeout=5)
            os.close(master)

    return run
