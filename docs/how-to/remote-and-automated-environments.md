# Remote and automated environments

conda-completion works in any terminal that sources your shell profile.
IDE integrated terminals, remote sessions, and containers all follow
the same rule: if `conda completion install` ran for that shell, TAB
completion works.

## IDE terminals

### VS Code, Cursor, Windsurf, Positron

VS Code and its forks (Cursor, Windsurf, Positron) all source your
shell profile (`.bashrc`, `.zshrc`, etc.) in the integrated terminal.
If you already ran `conda completion install`, completions work with
no extra setup.

Positron is particularly relevant for conda users since it targets
data science workflows and includes a terminal alongside its console
and notebook panels.

For Remote SSH and WSL, the hook needs to be installed on the remote
machine or inside WSL, not on the local host:

```bash
# on the remote machine or inside WSL
conda completion install
```

### JetBrains (PyCharm, IntelliJ, etc.)

The terminal tool window sources your shell profile. Completions work
if the hook is installed for the shell JetBrains runs (check
Settings > Tools > Terminal > Shell path).

For Remote Development via Gateway, install the hook on the remote
host.

### Zed

Zed's terminal panel sources your shell profile. Completions work if
the hook is installed. Zed defaults to your login shell.

### Neovim

Terminal buffers (`:terminal`) run your shell with its profile.
Completions work if the hook is installed for that shell.

### JupyterLab

The JupyterLab terminal runs your default shell. If the hook is
installed, completions work in the terminal panel. Note that
JupyterLab notebook cells (`!conda install ...`) do not go through
shell completion.

### Common pitfall

Some terminal configurations skip sourcing the full profile (e.g.,
non-login shells, custom shell paths). If completions work in a
standalone terminal but not in your IDE, check that the IDE's terminal
runs a login shell or sources the RC file where the hook was installed.
Run `conda completion status` inside the IDE terminal to verify the
hook is loaded.

## Containers

### Docker

For images used for interactive development (dev containers,
JupyterHub), generate the manifest at build time:

```dockerfile
FROM continuumio/miniconda3:latest

RUN conda install -y conda-completion && \
    conda completion install --yes bash && \
    conda clean -afy
```

`--yes` skips the interactive confirmation prompt.

### Dev containers (VS Code / GitHub Codespaces)

Add completion setup to `postCreateCommand`:

```json
{
  "postCreateCommand": "conda completion install --yes bash"
}
```

Or in the Dockerfile used by the dev container:

```dockerfile
RUN conda install -y conda-completion && \
    conda completion install --yes bash
```

### JetBrains dev containers

JetBrains Gateway supports dev containers through the Dev Containers
plugin. The same `postCreateCommand` approach works. Make sure the
shell path in the container matches the shell you installed the hook
for.

### Gitpod

Add completion setup to `.gitpod.yml`:

```yaml
tasks:
  - init: conda completion install --yes bash
```

Or include it in the Dockerfile referenced by your Gitpod config.

### DevPod

DevPod uses the dev container spec, so the `postCreateCommand`
approach from the VS Code section above works directly.

## CI

### GitHub Actions

To test that completions work after a plugin release:

```yaml
- uses: prefix-dev/setup-pixi@v0.9.6
  with:
    environments: test

- name: Generate and verify completions
  run: |
    pixi run -e test -- conda completion generate
    pixi run -e test -- conda completion status
```

### Caching the manifest

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/conda/completion
    key: conda-completion-${{ runner.os }}
```

The manifest invalidates automatically when the plugin set changes, so
a simple OS-based cache key works.

## Non-interactive environments

`generate` and `status` work without a TTY. `install` and `uninstall`
require `--yes` when no TTY is available.
