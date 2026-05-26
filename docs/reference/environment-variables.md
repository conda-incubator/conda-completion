# Environment variables

## Read by conda-completion

`CONDA_COMPLETION_SHELL`
: Overrides shell auto-detection. Accepts a shell name (`fish`) or
  full path (`/usr/local/bin/fish`). Takes priority over process tree
  detection and `SHELL`. PowerShell aliases such as `pwsh` are
  normalized to `powershell`. Useful when automatic detection fails or
  in scripted environments.

`SHELL`
: Fallback for shell detection when process tree walking does not find
  a known shell. Defaults to `powershell` on Windows if not set.

`CONDARC`
: Path to a custom `.condarc` file. The Rust completer reads this
  (in addition to `~/.condarc`) for channel name completion.

`HOME` (Unix) / `USERPROFILE` (Windows)
: Locates user-level files: `~/.conda/environments.txt`,
  `~/.condarc`, and `~/.conda/global/global.toml`.

`HOMEDRIVE` / `HOMEPATH`
: Windows fallback when `USERPROFILE` is not set.

## Rust completer

The binary (`_conda_completer`) gets its configuration from
command-line arguments (manifest path, shell name), not environment
variables. It reads `HOME`/`USERPROFILE` and `CONDARC` for global
context resolution.

## Standard conda variables

Not specific to conda-completion, but relevant:

`CONDA_CHANNELS`
: Overrides configured channels. Affects which packages appear in the
  manifest when `conda completion generate` extracts repodata.

## Cache paths

All data lives in the platform's user cache directory (via
`platformdirs`):

| Platform | Path |
| --- | --- |
| Linux | `~/.cache/conda/completion/` |
| macOS | `~/Library/Caches/conda/completion/` |
| Windows | `%LOCALAPPDATA%\conda\cache\completion\` |

See {doc}`/reference/manifest` for the files stored there.
