# Changelog

## Unreleased

## 0.1.0 (2026-05-21)

Initial release of conda-completion and conda-completer.

### Features

- Hybrid Python/Rust architecture: Python introspects conda's argparse
  tree (including all plugin subcommands) once, then a Rust binary handles
  every TAB press with sub-5ms response times.
- Automatically discovers and completes all conda plugin subcommands
  (workspace, global, self, spawn, task, etc.) without manual configuration.
- Reads project files in the working directory to complete environment
  names, task names, feature names, and channels.
- Supports conda.toml, pixi.toml, pyproject.toml, environment.yml,
  anaconda-project.yml, conda-project.yml, conda.lock, pixi.lock,
  conda-lock.yml, .condarc, environments.txt, and global.toml.
- Stat-based file cache tracks (mtime, size) tuples for every source
  file. Unchanged files are never re-parsed, keeping the hot path under
  5ms.
- Shell support for bash, zsh, PowerShell (Tier 1, fully tested) and
  fish (Tier 2, community-tested). Descriptions shown alongside candidates
  in zsh, fish, and PowerShell.
- A `conda_post_commands` hook detects when plugins are installed or
  removed and silently regenerates the completion manifest.
- Output sanitization strips control characters from candidates, file
  reads are size-limited (10MB), symlinks are rejected throughout the
  file walker and cache.

### Commands

- `conda completion generate` -- introspect conda's parser, write
  completion.toml manifest
- `conda completion install [shell]` -- generate + install shell RC hook
  (auto-detects shell)
- `conda completion uninstall [shell]` -- remove the RC hook
- `conda completion init <shell>` -- print the shell script to stdout

### Packages

- conda-completion: pure Python conda plugin with CLI and shell
  script generation.
- conda-completer: Rust binary (`_conda_completer`) that reads the
  TOML manifest and project files to produce TAB candidates. Built with
  maturin, ships platform-specific wheels.
