# conda-completion

Fast shell tab completion for conda and all its plugins.

A hybrid Python/Rust conda plugin that introspects conda's argparse tree
(including all plugin subcommands) and provides instant TAB completions
via a tiny Rust binary.

## Features

- Completes all conda commands, flags, and plugin subcommands
- Package name completion from repodata (`conda install nump<TAB>`)
- Version completion (`conda install numpy=<TAB>` lists available versions)
- Fuzzy matching for typos (`numpie` or `nupmy` suggest `numpy`)
- Contextual completions: environment names, task names, channels from
  project files (`conda.toml`, `pixi.toml`, `pyproject.toml`, `environment.yml`,
  `anaconda-project.yml`, `conda-project.yml`, lockfiles)
- Descriptions shown alongside candidates (zsh, fish, PowerShell)
- Fast response time (stat-cached context, no Python on the hot path)
- Shell support: bash, zsh, PowerShell (fully tested), fish (community-tested)
- Auto-regenerates the completion manifest when plugins are installed or removed

## Status

This project is in early development and available from conda-forge.

## Quick start (development)

```bash
# Clone and set up
git clone https://github.com/conda-incubator/conda-completion
cd conda-completion
pixi install
pixi run build

# Generate the completion manifest
conda completion generate

# Install the shell hook (auto-detects your shell)
conda completion install

# Or target a specific shell
conda completion install bash

# Or use eval directly in your RC file
eval "$(conda completion init bash)"
```

## How it works

conda-completion splits the work into two phases:

**Phase 1: Generation (Python, runs once).** `conda completion generate`
calls conda's `generate_parser()`, which loads all registered plugin
subcommands. The argparse tree is walked recursively to extract commands,
flags, positional arguments, help text, and package names from repodata.
The output is a `completion.msgpack` manifest plus `versions.index` and
`versions.store` package-version files in the platform cache directory.

**Phase 2: Completion (Rust, runs on every TAB).** When you press TAB,
your shell calls `_conda_completer`, a small Rust binary (~1 MB). It
reads the msgpack manifest for static command/flag/package completions,
then walks project files in your working directory for dynamic completions
(environment names, task names, channels). No Python runs on the hot
path. Package names are matched using a three-tier strategy (prefix,
substring, then fuzzy similarity) so typos like `numpie` still find
`numpy`.

A stat-based file cache tracks `(mtime, size)` for every source file.
If nothing changed since the last TAB press, the binary skips all
parsing and serves cached results directly.

### What files are read

**Project files** (walks upward from cwd, first match wins):

| File | What it provides |
| --- | --- |
| `conda.toml` / `pixi.toml` / `pyproject.toml` | Environment names, task names, feature names, channels |
| `anaconda-project.yml` | Environment names, command names |
| `conda-project.yml` | Environment names, command names |
| `environment.yml` | Environment name, channels |
| `conda.lock` / `pixi.lock` | Locked environment names and channels |
| `conda-lock.yml` | Channel names |

**Global state** (always read):

| File | What it provides |
| --- | --- |
| `~/.conda/environments.txt` | All registered environment names |
| `~/.condarc` | Configured channel names |
| `~/.conda/global/global.toml` | Globally installed tool names |

### CLI commands

| Command | Description |
| --- | --- |
| `conda completion generate` | Introspect conda's parser, write `completion.msgpack` |
| `conda completion refresh` | Force refresh package names and versions from repodata |
| `conda completion install [shell]` | Generate + install shell RC hook (auto-detects shell) |
| `conda completion uninstall [shell]` | Remove the RC hook |
| `conda completion init <shell>` | Print the shell script to stdout |
| `conda completion status` | Show cache, manifest, package-version, and binary diagnostics |

`install` and `uninstall` support `--dry-run` to preview changes and
`--yes` to skip confirmation.

`generate` and `install` support `--no-repodata` to skip package
metadata. Use `conda completion refresh` to force a repodata refresh.

## Development

```bash
pixi install
pixi run build       # build Rust binary (release)
pixi run build-debug # build Rust binary (debug)
pixi run test        # run Python + Rust integration tests
pixi run check       # lint + format + typecheck + clippy
```

## License

BSD-3-Clause
