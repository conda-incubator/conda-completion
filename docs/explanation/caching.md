# Caching

conda-completion has two caching layers: the completion manifest
(correctness first, regenerated infrequently) and the stat-based context
cache (speed first, updated on every TAB press).

## Manifest lifecycle

The completion manifest (`completion.msgpack`) is a snapshot of conda's
full command tree at generation time. It is created by
`conda completion generate` and changes when:

1. A conda plugin entry point is added or removed (detected via plugin
   entry point name hash comparison).
2. The user explicitly runs `conda completion generate`.

The `conda_post_commands` hook runs after every `conda install`,
`conda remove`, and `conda update`. It computes a SHA-256 hash of all
registered conda entry point names and compares it against the hash
stored in the manifest's `plugin_hash` field. If they differ, the
manifest is regenerated automatically.

The manifest stays consistent with plugins installed through conda. The
exception is plugins installed outside conda's package manager, which
bypass the conda hook system. See {doc}`/how-to/troubleshooting` for
the workaround.

The hash tracks entry point names, not parser contents. If a plugin
update changes argparse metadata without adding or removing a conda entry
point, run `conda completion generate` manually.

Package metadata is refreshed by `generate` when missing or older than
24 hours. If repodata refresh fails and existing package data is present,
generation preserves the existing package names and version files. If no
package data exists, command and flag completions are still generated.

## Stat-based context cache

The Rust completer checks project files (conda.toml, pixi.toml,
pyproject.toml, environment.yml, lockfiles) on every TAB press for
contextual completions (environment names, task names, channels).
Parsing files on every keypress would be too slow, so the binary
maintains a stat cache.

The cache maps file paths to `(mtime, size, extracted_data)` tuples.
On each TAB press, the binary stats each file and compares mtime and
size against cached values. If both match, the cached data is reused.
If either differs, the file is re-read, re-parsed, and the cache
updated.

```text
context_cache.msgpack:
{
  "/home/user/project/conda.toml": {
    "mtime_secs": 1716566400,
    "size": 1234,
    "env_names": ["dev", "test"],
    "task_names": ["build", "lint"],
    "feature_names": ["cuda"],
    "channels": ["conda-forge"]
  },
  "/home/user/.conda/environments.txt": {
    "mtime_secs": 1716480000,
    "size": 456,
    "env_names": ["base", "myproject"]
  }
}
```

Stored as `context_cache.msgpack` next to the manifest in the completion
cache directory.

### Eviction

The cache prunes stale entries on every save:

1. Entries for files that no longer exist are removed.
2. If more than 256 entries remain after pruning, the oldest (by mtime)
   are evicted until the count is within the limit.

The 256-entry cap is generous for typical usage (most users work in
fewer than 50 project directories) but prevents unbounded growth from
deleted or moved files.

### What gets cached

Project context (from the working directory upward):

- `conda.toml` / `pixi.toml`: workspace environments, tasks, features, channels
- `pyproject.toml`: `[tool.conda]` or `[tool.pixi]` sections
- `anaconda-project.yml`: env_specs, commands
- `conda-project.yml`: environments, commands
- `environment.yml`: name, channels
- Lockfiles (`conda.lock`, `pixi.lock`, `conda-lock.yml`): environments, channels

Global context (user home):

- `~/.conda/environments.txt`: registered environment names
- `~/.condarc` (and `$CONDARC`): configured channels
- `~/.conda/global/global.toml`: globally installed tool names for
  arguments explicitly marked as `global_tool`

Feature names may be retained in the context cache because workspace
manifests contain them, but no current completion type exposes feature
names directly.

### Parent directory walk

The binary walks up from the current working directory, checking each
level for project files. It stops at the first directory containing a
workspace-style or project file (`conda.toml`, `pixi.toml`,
`pyproject.toml` with `[tool.conda]` or `[tool.pixi]`,
`anaconda-project.yml`, or `conda-project.yml`). Lockfiles in the same
directory are also checked.

`conda.toml` is treated as a conda-workspaces manifest, not a formal
conda standard.

The walk also stops at VCS boundaries (`.git`, `.hg`, `.svn`), since
project files above a repository root are unlikely to be relevant.
Maximum walk depth is 10 levels.

## Version lookups

Package version data can be large for conda-forge-scale channel sets.
The version cache is split into `versions.index` and `versions.store`.
The index maps package names to byte ranges in the store, and the store
contains one msgpack-encoded version list per package.

The version cache is only loaded when the user types `=` in a package
spec (e.g., `numpy=<TAB>`), so version lookup cost does not affect
normal command, flag, or package-name completion latency.

See {doc}`/reference/manifest` for the file format.

## Cache files summary

| File | Updated by | Updated when | Purpose |
| --- | --- | --- | --- |
| `completion.msgpack` | Python (`generate`) | Plugin set changes or manual `generate` | Command tree, flags, package names |
| `versions.index` | Python (`generate`) | Missing, stale, or forced refresh | Package name to store offset mapping |
| `versions.store` | Python (`generate`) | Missing, stale, or forced refresh | Msgpack version-list records |
| `context_cache.msgpack` | Rust (every TAB) | Every cache miss | Stat-based file cache |
