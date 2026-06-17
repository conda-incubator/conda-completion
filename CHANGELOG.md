# Changelog

## Unreleased

### Documentation

- Removed generated demo videos from the repository.

## 0.3.0 (2026-06-14)

### Features

- Added context-aware completion metadata for conda plugins, including explicit completion types, rule-based positional completions, runtime directory sources, and manifest-provided command aliases.
- Added `--command-name` and `CONDA_COMPLETION_COMMAND_NAME` so shell hooks can target wrapper executables such as `cx`.
- Added static completions for conda configuration parameters and conda doctor health checks.
- Fish installs now write a generated autoload completion file instead of running `conda completion init fish` on every new shell startup.
- Environment positional completions now include both named environments and registered environment prefixes.

### Fixes

- Fixed zsh completion display so candidates and descriptions stay aligned without relying on `_describe`.
- Fixed environment-name completion for positional arguments that should include prefix paths.
- Improved failure handling when static completion sources cannot be collected from the installed conda runtime.

### Documentation

- Expanded wrapper-command, fish autoload, manifest, and completer binary documentation to match the current implementation.

## 0.2.0 (2026-05-28)

### Breaking Changes

- Manifest format changed from TOML to msgpack. Regenerate with `conda completion generate` after upgrading.
- Stat cache format changed from TOML to msgpack (`context_cache.msgpack`). The cache is rebuilt automatically on first TAB press.
- Python dependencies: `msgpack >=1.0` replaces `tomli` and `tomli-w`.
- Rust dependencies: `rmp-serde` replaces `serde_json` (which was unused).

### Features

- Package name completion from repodata. `conda install nump<TAB>` completes package names extracted from configured channels during `conda completion generate`.
- Version completion. `conda install numpy=<TAB>` and `conda install numpy==<TAB>` list available versions. Versions are stored in indexed `versions.index` and `versions.store` files, loaded only when `=` is detected in the current word.
- Three-tier fuzzy matching for package names: prefix > substring > normalized Damerau-Levenshtein similarity. Typos like `numpie` or `nupmy` suggest `numpy`. The similarity threshold is 0.6 with a cap of 10 results.
- `conda completion refresh` to force-refresh package names and versions from repodata.
- `--no-repodata` for `conda completion generate` and `conda completion install` to skip package metadata in offline or automated environments.
- `--cache-dir` and `CONDA_COMPLETION_CACHE_DIR` for overriding the completion cache directory.
- `--versions` CLI argument for the Rust binary to specify the versions index path (defaults to `versions.index` alongside the manifest).

### Performance

- Manifest deserialization is faster with msgpack (binary format, no string parsing).
- Package name completion uses the pre-built name list from `completion.msgpack` (~500KB), avoiding repodata access on every TAB press.
- Version completion loads `versions.index` and one record from `versions.store` only when `=` is detected, keeping the common case fast.
- Fuzzy matching over 30k+ package names runs in under 1ms (Damerau-Levenshtein is O(nm) per comparison, but for short package names this is ~900 ops each).

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
  msgpack manifest and project files to produce TAB candidates. Built with
  maturin, ships platform-specific wheels.
