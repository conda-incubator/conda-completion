# conda-completion

Fast shell tab completion for conda and all its plugins.

A hybrid Python/Rust conda plugin that introspects conda's argparse tree
(including all plugin subcommands) and provides instant TAB completions
via a tiny Rust binary.

## Features

- Completes all conda commands, flags, and plugin subcommands
- Contextual completions: environment names, task names, channels from
  project files (conda.toml, pixi.toml, pyproject.toml, environment.yml)
- Descriptions shown alongside candidates (zsh, fish, PowerShell)
- Sub-5ms response time (stat-cached context, no Python on the hot path)
- Shell support: bash, zsh, PowerShell (fully tested), fish (community-tested)
- Auto-regenerates the completion manifest when plugins are installed or removed

## Status

This project is in early development. It is not yet published to conda-forge.

## Quick start (development)

```bash
# clone and set up
git clone https://github.com/conda-incubator/conda-completion
cd conda-completion
pixi install
pixi run build

# generate the completion manifest
conda completion generate

# add to your shell (one of):
conda completion install bash
conda completion install zsh
conda completion install powershell
conda completion install fish

# or use eval directly in your RC file:
eval "$(conda completion init bash)"
```

## How it works

1. `conda completion generate` introspects conda's full argparse tree
   (including all installed plugin subcommands) and writes a TOML manifest.
2. On every TAB press, a small Rust binary (`_conda_completer`, ~500KB) reads
   the manifest and walks local project files to produce candidates. No
   Python runs on the hot path.
3. A stat-based cache avoids re-parsing files that have not changed since
   the last TAB press.

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
