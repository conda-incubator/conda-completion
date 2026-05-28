# Remote and automated environments

conda-completion works in terminals that load the startup file containing
its hook. IDE integrated terminals, remote sessions, and containers all
follow the same rule: install the hook where that shell session actually
starts.

## IDE terminals

### VS Code, Cursor, Windsurf, Positron

VS Code and related editors usually start the integrated terminal with
your configured shell. If that shell reads the startup file where
`conda completion install` wrote its hook, completions are available in
the integrated terminal.

For Remote SSH and WSL, the hook needs to be installed on the remote
machine or inside WSL, not on the local host:

```bash
# on the remote machine or inside WSL
conda completion install
```

### JetBrains (PyCharm, IntelliJ, etc.)

The terminal tool window sources your shell profile. Completions work
if the hook is installed for the shell JetBrains runs (check
`Settings > Tools > Terminal > Shell path`).

For Remote Development via Gateway, install the hook on the remote
host.

### Zed

Zed's terminal panel uses your configured shell. Completions are
available when that shell reads the startup file containing the hook.

### Neovim

Terminal buffers (`:terminal`) run your shell with its profile.
Completions work if the hook is installed for that shell.

### JupyterLab

The JupyterLab terminal runs your default shell. If the hook is
installed, completions work in the terminal panel. Note that
JupyterLab notebook cells (`!conda install ...`) do not go through
shell completion.

### Common pitfall

Some terminal configurations skip the full profile (for example,
non-login shells or custom shell paths). If completions work in a
standalone terminal but not in your IDE, check that the IDE's terminal
loads the file where the hook was installed. Run `conda completion
status` inside the IDE terminal to confirm the manifest and binary come
from the environment you expect.

## Containers

### Docker

For images used for interactive development (dev containers,
JupyterHub), generate the manifest at build time:

```dockerfile
FROM continuumio/miniconda3:latest

RUN conda install -y -c conda-forge conda-completion && \
    conda completion install bash --yes && \
    conda clean -afy
```

`--yes` skips the interactive confirmation prompt.

For faster image builds that do not need package name or version
completion, add `--no-repodata` to the install command.

If the container switches from `root` to a non-root user, run the install
step as the final user or regenerate after switching users. The manifest
lives in the current user's cache directory.

### Dev containers (VS Code / GitHub Codespaces)

Add completion setup to `postCreateCommand`:

```json
{
  "postCreateCommand": "conda completion install bash --yes"
}
```

Or in the Dockerfile used by the dev container:

```dockerfile
RUN conda install -y -c conda-forge conda-completion && \
    conda completion install bash --yes
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
  - init: conda completion install bash --yes
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

After `conda install`, `conda remove`, or `conda update`, the manifest
is regenerated when registered conda entry point names changed, so a
simple OS-based cache key is usually enough. If a job updates a plugin
without changing its entry point name, run `conda completion generate`
before testing completions.

This cache directory also contains `versions.index` and `versions.store`
when package metadata has been generated.

For jobs that only validate plugin command metadata, prefer:

```yaml
- name: Generate command completions
  run: conda completion generate --no-repodata
```

This avoids network-dependent repodata reads.

## Non-interactive environments

`generate` and `status` work without a TTY. `install` and `uninstall`
require `--yes` when no TTY is available.

See {doc}`offline-and-restricted-networks` for private mirrors,
air-gapped setups, and restricted network behavior.
