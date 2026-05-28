# Performance

Shell completion has a tight latency budget. Users press TAB repeatedly,
and visible delays interrupt command-line editing.

## Design for speed

conda-completion avoids the two main sources of latency in shell
completion:

1. **No Python on the hot path.** The Rust binary is the only thing that
   runs on TAB press. Python startup can already be perceptible before
   conda imports plugins or configuration.

2. **No file re-parsing on repeat presses.** A stat-based file cache
   tracks which project and global files have changed. If nothing
   changed since the last TAB press (the common case), the binary skips
   all TOML/YAML parsing and reads pre-parsed results from a small
   cache file.

## What happens on each TAB press

**Common case (commands, flags, package names):**

1. `stat()` each source file (one syscall per file)
2. Compare against cached `(mtime, size)` tuples
3. On cache hit: read pre-parsed results from `context_cache.msgpack`
4. Read `completion.msgpack` (command tree + package names)
5. Prefix-filter candidates and output

This path is fast because it does no parsing, just binary file reads
and string comparisons.

**Version completion (when `=` is detected):**

Same as above, plus loading `versions.index` and one record from
`versions.store` for the requested package. This path does extra I/O
and msgpack decoding, so version completion is slower than command or
package name completion, but it avoids deserializing every package's
versions for one lookup.

**Fuzzy matching (when no prefix or substring match exists):**

Same as the common case, but instead of a simple prefix filter, runs
normalized Damerau-Levenshtein similarity scoring over all package
names. This is the slowest path, and only runs after prefix and
substring matching return no results.

## The stat cache

The stat cache is the key optimization. On each invocation:

1. Call `stat()` on every source file. One syscall per file.
2. Compare each file's `(mtime, size)` tuple against cached values.
3. If all match (the common case), read pre-parsed candidates from
   `context_cache.msgpack`. No TOML/YAML parsing at all.
4. If any file changed, re-parse only that file. Merge with cached
   results for unchanged files. Write the updated cache atomically
   (write to `.tmp`, then rename).

### Why stat and not content hashing?

Content hashing (e.g., xxhash of file contents) requires reading the
entire file before deciding whether to parse it. `stat()` answers the
same question with a single syscall that reads only filesystem metadata.
The only false-negative case (content changes without mtime or size
changing) is vanishingly rare in normal editing workflows.

## Fuzzy matching

When no prefix or substring match is found, the binary falls back to
normalized Damerau-Levenshtein similarity. This handles common typos
like transpositions ("nupmy" for "numpy") and near-misses ("numpie"
for "numpy").

The matching uses a three-stage strategy to avoid unnecessary work:

1. **Prefix match**: return immediately if any candidates start with the
   query. This is the common case and is essentially free.
2. **Substring match**: return if any candidates contain the query.
   Still fast, one pass over the candidate list.
3. **Similarity**: only runs when the first two stages return nothing. Scores
   are filtered at a 0.6 threshold and capped at 10 results.

## Comparison with existing tools

| Tool | Approach |
|---|---|
| `conda-bash-completion` | Runs `conda --help` on every TAB press, parses output with sed/awk |
| `conda-zsh-completion` | Hand-written static script with 12-hour package cache |
| Fish built-in `conda.fish` | Static script (based on conda 4.4.11) |
| `argc-completions` | Generic `--help` parser |
| **conda-completion** | **Pre-generated msgpack manifest, Rust binary, stat-cached context** |

The key difference is that conda-completion never starts a Python
process on TAB press. Tools that run `conda --help` or similar pay
Python's startup cost on every keypress.

## Binary size

The Rust binary is compiled with LTO (link-time optimization), size
optimization (`opt-level = "z"`), and symbol stripping. Dependencies
are kept minimal:

| Dependency | Purpose |
|---|---|
| `serde` + `rmp-serde` | msgpack manifest and cache deserialization |
| `serde` + `toml` | TOML workspace/project file parsing (conda.toml, pixi.toml) |
| `serde-saphyr` | YAML parsing (environment.yml, .condarc, lockfiles) |
| `fs-err` | Better I/O errors |

Heavier alternatives were evaluated and rejected:

- **rattler crates** (`rattler_conda_types`, `rattler_lock`): pull in
  nom, regex, simd-json, rayon, purl, fancy-regex. Significant binary
  size and startup overhead for functionality we don't need.
- **clap_complete**: adds clap's full argument parsing framework.
  Unnecessary when the completion engine is custom.
- **serde_yml**: unmaintained, has a RUSTSEC advisory (RUSTSEC-2025-0068).
  Replaced by serde-saphyr (pure Rust, actively maintained).
