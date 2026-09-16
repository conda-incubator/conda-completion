# Changelog

## Unreleased

## 0.3.1 (2026-09-16)

After upgrading, run `conda completion generate` and restart your shell. Fish users should also run `conda completion install fish` to refresh the installed completion file before restarting.

### Security

- Quote Bash and PowerShell completion values so spaces and backslashes remain part of a single literal argument.
- Use Fish-specific escaping for executable and cache paths containing backslashes or apostrophes.
- Use private temporary directories with cleanup on exit when recording demos.

### Fixes

- Restore completion of environment names and registered prefixes after `conda activate`.
- Remove the unintended `cc` console script from the conda recipe.

### Maintenance

- Remove unused Rust and development dependencies and generated demo videos.

## 0.3.0 (2026-06-14)

- Added `--command-name` and `CONDA_COMPLETION_COMMAND_NAME` so shell hooks can target wrapper executables such as `cx`.
- Added plugin-provided completion metadata for explicit completion types, rule-based positional completions, runtime directory sources, and manifest-provided command aliases.
- Added static completions for conda configuration parameters and conda doctor health checks.
- Fish installs now write a generated autoload completion file instead of running `conda completion init fish` during shell startup.
- Environment positional completions now include registered environment prefixes as well as named environments.
- Fixed zsh completion display so candidates and descriptions stay aligned in the generated zsh function.

## 0.2.0 (2026-05-28)

- Manifest and context cache files now use msgpack.
- Package names and versions are extracted from repodata for install/remove-style completions.
- Version data is stored in indexed `versions.index` and `versions.store` files.
- Added `conda completion refresh` to force-refresh package metadata.
- Added `--no-repodata` for `generate` and `install` in offline or automated environments.
- Added `conda completion --cache-dir` and `CONDA_COMPLETION_CACHE_DIR` for overriding the completion cache directory.
- Added fuzzy package matching for prefix, substring, and near-miss queries.

## 0.1.0 (2026-05-21)

- Initial release of conda-completion and conda-completer.
