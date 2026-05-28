# Configuration

Most users only need `conda completion install`. The settings below are
available for scripts, custom shell startup files, and cache inspection.

## Shell detection

By default, `conda completion install` (without a shell argument) detects
your shell from `CONDA_COMPLETION_SHELL`, the parent process tree, the
`SHELL` environment variable, and finally a platform default. On Windows,
the platform default is PowerShell.

To override:

```bash
conda completion install zsh
```

Or in scripts:

```bash
CONDA_COMPLETION_SHELL=zsh conda completion install --yes
```

## Manifest location

The completion manifest is stored in your platform's cache directory:

| Platform | Path |
|---|---|
| Linux | `~/.cache/conda/completion/completion.msgpack` |
| macOS | `~/Library/Caches/conda/completion/completion.msgpack` |
| Windows | `%LOCALAPPDATA%\conda\cache\completion\completion.msgpack` |

Package version data lives in `versions.index` and `versions.store` in
the same directory. These files are only loaded when `=` is detected in
the current word (e.g., `numpy=<TAB>`).

This follows the same pattern as conda's own cache directories, using
`platformdirs.user_cache_dir("conda")`.

To store completion data somewhere else for one command, pass
`--cache-dir` before the subcommand:

```bash
conda completion --cache-dir /path/to/conda-completion-cache generate
conda completion --cache-dir /path/to/conda-completion-cache status
```

The option names the directory containing `completion.msgpack`,
`versions.index`, `versions.store`, and `context_cache.msgpack`. For a
persistent process-level override, set `CONDA_COMPLETION_CACHE_DIR`.
Precedence follows conda's usual shape: command-line option, then
environment variable, then default cache location.

If `conda completion --cache-dir /path/to/cache install zsh` installs a
shell startup hook, that hook keeps using `/path/to/cache` by passing the
same option to `conda completion init zsh`.

## Context cache

The stat-based context cache lives alongside the manifest:

```
<completion_cache_dir>/context_cache.msgpack
```

This file maps source file paths to their parsed data (environment names,
task names, channels) along with the file's mtime and size at parse time.
On each TAB press, the completer stats each source file and only re-parses
files whose mtime or size has changed.

Deleting this file is safe. It will be rebuilt on the next TAB press at the
cost of re-parsing all project and global files on the next invocation.

## Manual regeneration

If you install a conda plugin outside conda's package manager, or update
a plugin without changing its conda entry point name, regenerate
manually:

```bash
conda completion generate
```

By default, generation reuses package metadata if it is less than 24
hours old. Use `conda completion refresh` to force conda-completion to
rebuild package metadata from conda repodata, or `--no-repodata` to
regenerate command and flag completions without package metadata.

## Eval-based setup

Instead of using `conda completion install`, you can add the eval line
directly to your RC file:

:::::{tab-set}

::::{tab-item} bash

```bash
eval "$(conda completion init bash)"
```

::::

::::{tab-item} zsh

```zsh
eval "$(conda completion init zsh)"
```

::::

::::{tab-item} PowerShell

```powershell
conda completion init powershell | Invoke-Expression
```

::::

::::{tab-item} fish

```fish
conda completion init fish | source
```

::::

:::::

The automatic fish installer writes to
`~/.config/fish/completions/conda.fish`. The manual eval line can live
there or in `~/.config/fish/config.fish`.
