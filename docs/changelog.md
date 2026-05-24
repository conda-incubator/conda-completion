# Changelog

## Unreleased

- Initial release of conda-completion.
- Hybrid Python/Rust architecture: Python introspects, Rust completes.
- Plugin-aware: all conda plugin subcommands are included automatically.
- Contextual completions from project files (conda.toml, pixi.toml,
  pyproject.toml, environment.yml, lockfiles, .condarc, global.toml).
- Tier 1 shell support: bash, zsh, PowerShell.
- Tier 2 shell support: fish.
- Automatic manifest regeneration via `conda_post_commands` hook.
- Install/uninstall commands for shell RC file management.
- Fast response time for command, flag, and package name completion (no Python on the hot path).
