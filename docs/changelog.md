# Changelog

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
