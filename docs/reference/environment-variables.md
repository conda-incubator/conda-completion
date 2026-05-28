# Environment variables

## Read by conda-completion

`CONDA_COMPLETION_SHELL`
: Overrides shell auto-detection. Accepts a shell name (`fish`) or
  full path (`/usr/local/bin/fish`). Takes priority over process tree
  detection and `SHELL`. PowerShell aliases such as `pwsh` are
  normalized to `powershell`. Useful when automatic detection fails or
  in scripted environments.

`CONDA_COMPLETION_CACHE_DIR`
: Overrides the directory that stores `completion.msgpack`,
  `versions.index`, `versions.store`, and `context_cache.msgpack`. Use
  this in CI, containers, or locked-down environments where the platform
  user cache directory is not appropriate. Set it consistently when
  running `generate`, `install`, `init`, and `status`. The
  `conda completion --cache-dir PATH` command-line option takes
  precedence over this environment variable.

`SHELL`
: Fallback for shell detection when process tree walking does not find
  a known shell. Defaults to `powershell` on Windows if not set.

`CONDARC`
: Path to a custom {external+conda:doc}`.condarc
  <user-guide/configuration/use-condarc>` file. The Rust completer reads
  this (in addition to `~/.condarc`) for channel name completion. On
  Windows, `C:\ProgramData\conda\.condarc` is also checked when present.

`HOME` (Unix) / `USERPROFILE` (Windows)
: Locates user-level files: `~/.conda/environments.txt`,
  `~/.condarc`, and `~/.conda/global/global.toml`.

`HOMEDRIVE` / `HOMEPATH`
: Windows fallback when `USERPROFILE` is not set.

## Rust completer

The binary (`_conda_completer`) gets its configuration from command-line
arguments (manifest path, shell name), not conda-completion-specific
environment variables. `CONDA_COMPLETION_CACHE_DIR` affects the manifest
path passed to the binary by `conda completion init`; the binary does
not read that variable directly. It reads `HOME`/`USERPROFILE` and
`CONDARC` for global context resolution.

## Standard conda variables

Not specific to conda-completion, but relevant:

`CONDA_CHANNELS`
: Overrides configured channels. Affects which packages appear in the
  manifest when `conda completion generate` extracts repodata.

## Cache paths

By default, all data lives in the platform's user cache directory (via
`platformdirs`):

| Platform | Path |
| --- | --- |
| Linux | `~/.cache/conda/completion/` |
| macOS | `~/Library/Caches/conda/completion/` |
| Windows | `%LOCALAPPDATA%\conda\cache\completion\` |

Set `CONDA_COMPLETION_CACHE_DIR` to use a different directory, or pass
`conda completion --cache-dir PATH` for a single command.

See {doc}`/reference/manifest` for the files stored there.
