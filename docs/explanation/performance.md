# Performance

Shell completion must feel instant. Users press TAB reflexively and any
perceptible delay breaks flow. conda-completion targets sub-5 ms
response times on the common path.

## Budget

| Phase | Target | Typical |
|---|---|---|
| Binary startup | < 1 ms | ~0.5 ms |
| Manifest read | < 2 ms | ~1.5 ms |
| Context resolution (cache hit) | < 2 ms | ~1.5 ms |
| Context resolution (cache miss) | < 15 ms | ~12 ms |
| **Total (cache hit)** | **< 5 ms** | **~4 ms** |
| **Total (cache miss)** | **< 20 ms** | **~17 ms** |

The binary size target is under 1 MB (typical: ~850 KB). Memory usage
stays under 10 MB (typical: ~5 MB).

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
- Tiny binary footprint (under 1 MB)

## The stat cache

The largest performance gain comes from the stat-based file cache. The
Rust binary reads several files on each invocation: the TOML manifest,
project files (conda.toml, pixi.toml), global state (environments.txt,
.condarc), and potentially lockfiles.

Parsing all of these on every TAB press takes 12-17 ms. But files
rarely change between keystrokes. The cache exploits this:

1. On each invocation, call `stat()` on every source file. This is one
   syscall per file, totaling roughly 0.1 ms for 5-8 files.
2. Compare each file's `(mtime, size)` tuple against the cached values.
3. If all match (the common case), read the pre-parsed completion
   candidates from `context_cache.toml`. Skip all TOML/YAML/JSON
   parsing.
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
| **conda-completion** | **TOML manifest + Rust binary** | **3-5 ms** |

## Where time is spent

On a cache hit (the common case):

```text
stat() calls for 6 files      0.1 ms
read context_cache.toml        1.0 ms
read completion.toml           1.5 ms
command-line parsing           0.2 ms
prefix filtering + output      0.2 ms
                              ──────
total                          3.0 ms
```

On a cache miss (a file was edited):

```text
stat() calls for 6 files      0.1 ms
detect changed file            0.1 ms
parse changed file (TOML)      2.0 ms
read cached results for rest   1.0 ms
write context_cache.toml       1.5 ms
read completion.toml           1.5 ms
command-line parsing           0.2 ms
prefix filtering + output      0.2 ms
                              ──────
total                          6.6 ms
```

YAML files (.condarc, environment.yml) take slightly longer to parse
(3-5 ms) than TOML files (1-2 ms) due to the format's complexity, but
these files change infrequently.

## Binary size

The Rust binary is compiled with LTO (link-time optimization), size
optimization (`opt-level = "z"`), and symbol stripping. Dependencies
are kept minimal:

| Dependency | Purpose | Size contribution |
|---|---|---|
| `serde` + `toml` | TOML parsing | ~400 KB |
| `serde-saphyr` | YAML parsing | ~200 KB |
| `serde_json` | JSON lockfiles | ~100 KB |
| `fs-err` | Better I/O errors | ~10 KB |

Heavier alternatives were evaluated and rejected:

- **rattler crates** (`rattler_conda_types`, `rattler_lock`): pull in
  nom, regex, simd-json, rayon, purl, fancy-regex. Binary would grow
  from under 1 MB to 5-10 MB with 50 ms startup overhead.
- **clap_complete**: adds clap's full argument parsing framework.
  Unnecessary when the completion engine is custom.
- **serde_yml**: unmaintained, has a RUSTSEC advisory (RUSTSEC-2025-0068).
  Replaced by serde-saphyr (pure Rust, actively maintained).
