# Performance

Shell completion must feel instant. Users press TAB reflexively and any
perceptible delay breaks flow. conda-completion targets sub-5 ms
response times on the common path.

## Budget

| Phase | Target | Typical |
|---|---|---|
| Binary startup | < 1 ms | ~0.5 ms |
| Manifest read (msgpack) | < 2 ms | ~1.0 ms |
| Context resolution (cache hit) | < 2 ms | ~1.5 ms |
| Context resolution (cache miss) | < 15 ms | ~12 ms |
| Package name matching (30k+ names) | < 2 ms | ~1.0 ms |
| Version file load (on `=` only) | < 10 ms | ~5 ms |
| **Total (cache hit, no packages)** | **< 5 ms** | **~4 ms** |
| **Total (package name completion)** | **< 7 ms** | **~5 ms** |
| **Total (version completion)** | **< 15 ms** | **~10 ms** |
| **Total (cache miss)** | **< 20 ms** | **~17 ms** |

The binary size target is under 1.5 MB (typical: ~1 MB). Memory usage
stays under 15 MB (typical: ~8 MB with versions loaded).

## Why Rust?

Shell completion scripts typically use one of two approaches:

**Parse help text on every TAB press.** Tools like
`conda-bash-completion` run `conda --help` or `conda install --help`
and parse the output with sed/awk. This starts a Python process on
every keypress, taking 100-300 ms.

**Hand-maintained static scripts.** Tools like `conda-zsh-completion`
ship a hand-written completion script. Fast, but requires manual
updates whenever conda adds or changes commands. No plugin awareness.

conda-completion takes a third path: generate once, complete fast. The
generation step uses Python (necessary for argparse introspection), but
the completion step uses Rust. This gives us:

- No Python startup cost on TAB press
- A single statically linked binary with no runtime dependencies
- Predictable, consistent performance across platforms
- Tiny binary footprint (under 1.5 MB, typical ~1 MB)

## The stat cache

The largest performance gain comes from the stat-based file cache. The
Rust binary reads several files on each invocation: the msgpack manifest,
project files (conda.toml, pixi.toml), global state (environments.txt,
.condarc), and potentially lockfiles.

Parsing all of these on every TAB press takes 12-17 ms. But files
rarely change between keystrokes. The cache exploits this:

1. On each invocation, call `stat()` on every source file. This is one
   syscall per file, totaling roughly 0.1 ms for 5-8 files.
2. Compare each file's `(mtime, size)` tuple against the cached values.
3. If all match (the common case), read the pre-parsed completion
   candidates from `context_cache.msgpack`. Skip all TOML/YAML parsing.
4. If any file changed, re-parse only that file. Merge results with
   the still-valid cached entries. Write the updated cache atomically.

Cache writes use a write-to-temp-then-rename pattern to prevent
corruption if the shell or process is interrupted mid-write.

### Why stat and not content hashing?

Content hashing (e.g., xxhash of file contents) requires reading the
entire file before deciding whether to parse it. For a 50 KB
conda.toml, that is 50 KB of I/O just to check freshness.

`stat()` answers the same question with a single syscall that reads
only filesystem metadata. The only case where stat-based caching gives
a false negative is when a file's content changes but its mtime and size
do not, which is vanishingly rare in normal editing workflows.

## Comparison with existing tools

| Tool | Approach | Typical latency |
|---|---|---|
| `conda-bash-completion` | Parse `--help` output | 100-300 ms |
| `conda-zsh-completion` | Static script, 12h package cache | 10-20 ms |
| Fish built-in `conda.fish` | Static script | 5-10 ms |
| `argc-completions` | Generic `--help` parser | 50-100 ms |
| **conda-completion** | **msgpack manifest + Rust binary** | **3-5 ms** |

## Where time is spent

On a cache hit (the common case, command/flag completion):

```text
stat() calls for 6 files          0.1 ms
read context_cache.msgpack         0.8 ms
read completion.msgpack            1.0 ms
command-line parsing               0.2 ms
prefix filtering + output          0.2 ms
                                  ──────
total                              2.3 ms
```

On a cache hit with package name completion:

```text
stat() calls for 6 files          0.1 ms
read context_cache.msgpack         0.8 ms
read completion.msgpack            1.0 ms
command-line parsing               0.2 ms
package name matching (30k+)       1.0 ms
prefix filtering + output          0.2 ms
                                  ──────
total                              3.3 ms
```

On a cache hit with version completion (when `=` is detected):

```text
stat() calls for 6 files          0.1 ms
read context_cache.msgpack         0.8 ms
read completion.msgpack            1.0 ms
read versions.msgpack              5.0 ms
command-line parsing               0.2 ms
version prefix filtering           0.2 ms
                                  ──────
total                              7.3 ms
```

On a cache miss (a file was edited):

```text
stat() calls for 6 files          0.1 ms
detect changed file                0.1 ms
parse changed file (TOML)          2.0 ms
read cached results for rest       0.8 ms
write context_cache.msgpack        1.0 ms
read completion.msgpack            1.0 ms
command-line parsing               0.2 ms
prefix filtering + output          0.2 ms
                                  ──────
total                              5.4 ms
```

YAML files (.condarc, environment.yml) take slightly longer to parse
(3-5 ms) than TOML files (1-2 ms) due to the format's complexity, but
these files change infrequently.

## Fuzzy matching

When no prefix or substring match is found for a package name, the
binary falls back to normalized Damerau-Levenshtein similarity. This
handles common typos like transpositions ("nupmy" for "numpy") and
near-misses ("numpie" for "numpy").

Running Damerau-Levenshtein over 30,000+ package names sounds expensive,
but each comparison is O(n*m) where n and m are the lengths of the two
strings. Package names average 8-12 characters, so each comparison is
roughly 100 operations. At 30,000 comparisons, that is about 3 million
operations, which completes in under 1 ms on modern hardware.

The matching uses a three-tier strategy to avoid unnecessary work:

1. **Prefix match**: return immediately if any candidates start with the
   query. This is the common case and is essentially free (string
   comparison).
2. **Substring match**: return if any candidates contain the query.
   Still fast, one pass over the candidate list.
3. **Similarity**: only runs when tiers 1 and 2 return nothing. Scores
   are filtered at a 0.6 threshold and capped at 10 results to keep
   output manageable.

## Binary size

The Rust binary is compiled with LTO (link-time optimization), size
optimization (`opt-level = "z"`), and symbol stripping. Dependencies
are kept minimal:

| Dependency | Purpose | Size contribution |
|---|---|---|
| `serde` + `rmp-serde` | msgpack manifest and cache deserialization | ~150 KB |
| `serde` + `toml` | TOML project file parsing (conda.toml, pixi.toml) | ~400 KB |
| `serde-saphyr` | YAML parsing (environment.yml, .condarc, lockfiles) | ~200 KB |
| `fs-err` | Better I/O errors | ~10 KB |

Heavier alternatives were evaluated and rejected:

- **rattler crates** (`rattler_conda_types`, `rattler_lock`): pull in
  nom, regex, simd-json, rayon, purl, fancy-regex. Binary would grow
  from under 1 MB to 5-10 MB with 50 ms startup overhead.
- **clap_complete**: adds clap's full argument parsing framework.
  Unnecessary when the completion engine is custom.
- **serde_yml**: unmaintained, has a RUSTSEC advisory (RUSTSEC-2025-0068).
  Replaced by serde-saphyr (pure Rust, actively maintained).
