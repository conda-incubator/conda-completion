# Features

## Plugin-aware completion

conda-completion introspects conda's full argparse tree after all plugins
have loaded. Every plugin that registers subcommands via `conda_subcommands`
is automatically included. No configuration, no opt-in required.

Installed plugin commands are completed with the same fidelity as built-in
commands: subcommands, flags, flag values, and help descriptions.

## Contextual completions

The completer reads your project files to provide context-aware candidates:

| What's completed | Source files |
|---|---|
| Environment names | `conda.toml`, `pixi.toml`, `pyproject.toml`, `environment.yml`, `conda.lock`, `pixi.lock`, `anaconda-project.yml`, `conda-project.yml`, `~/.conda/environments.txt` |
| Task names | `conda.toml`, `pixi.toml`, `pyproject.toml`, `anaconda-project.yml`, `conda-project.yml` |
| Feature names | `conda.toml`, `pixi.toml`, `pyproject.toml` |
| Channel names | `conda.toml`, `pixi.toml`, `pyproject.toml`, `conda-lock.yml`, `conda.lock`, `pixi.lock`, `.condarc` |
| Global tool names | `~/.conda/global/global.toml` |

## Descriptions alongside candidates

In shells that support it (zsh, fish, PowerShell), each candidate is shown
with its help text:

:::{image} ../demos/option-completion.gif
:alt: Option completion with descriptions
:width: 100%
:::

```text
$ conda install --<TAB>
--channel     -- Additional channel to search for packages
--dry-run     -- Only display what would have been done
--name        -- Name of environment
--prefix      -- Full path to environment location
```

## Sub-5 ms response time

A tiny Rust binary (under 1 MB) handles every TAB press. No Python process
starts on the hot path. A stat-based file cache avoids re-parsing files
that have not changed since the last TAB press.

| Scenario | Typical time |
|---|---|
| Cache hit (common case) | < 5 ms |
| Cache miss (file changed) | < 20 ms |

## Automatic manifest regeneration

After `conda install`, `conda remove`, or `conda update`, a post-command
hook checks whether the set of registered plugins has changed. If it has,
the completion manifest is regenerated automatically. You never need to
run `conda completion generate` manually after installing a plugin via
conda.

## Tiered shell support

| Shell | Tier | Notes |
|---|---|---|
| bash | Tier 1 | Fully tested in CI on every push |
| zsh | Tier 1 | Fully tested in CI on every push |
| PowerShell | Tier 1 | Fully tested in CI on every push |
| fish | Tier 2 | Community-tested, best-effort |

## Install and uninstall commands

`conda completion install` and `conda completion uninstall` manage a
delimited block in your shell's RC file. The install command is
idempotent (running it twice does not duplicate the block) and supports
`--dry-run` to preview changes without writing.
