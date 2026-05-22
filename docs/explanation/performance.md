# Performance

Shell completion must feel instant. Users press TAB reflexively and any
perceptible delay breaks flow. conda-completion targets sub-10 ms
response times for the common case (command, flag, and package name
completion).

## Measured performance

All measurements taken with the release binary on macOS (Apple Silicon),
28,500 packages from conda-forge, warm stat cache, using `/usr/bin/time`.

| Operation | Time | Memory |
|---|---|---|
| Subcommand completion | < 1 ms | ~5 MB |
| Flag completion | < 1 ms | ~5 MB |
| Context completion (env names, channels) | < 1 ms | ~5 MB |
| Package name prefix match (28k names) | < 1 ms | ~7 MB |
| Version completion (`numpy=`, loads versions.msgpack) | ~35 ms | ~25 MB |
| Fuzzy matching (Damerau-Levenshtein over 28k names) | ~60 ms | ~7 MB |

The common operations (subcommands, flags, package name prefix) are
effectively instant. Version completion and fuzzy matching are slower
because they do more work, but both complete well within the threshold
where a user would notice delay.

**Binary size:** ~900 KB (release, with LTO and symbol stripping).

**Cache files:**

| File | Typical size |
|---|---|
| `completion.msgpack` | ~500 KB |
| `versions.msgpack` | ~2-3 MB |
| `context_cache.msgpack` | < 10 KB |

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

## The stat cache

The largest performance gain comes from the stat-based file cache. The
Rust binary reads several files on each invocation: the msgpack manifest,
project files (conda.toml, pixi.toml), global state (environments.txt,
.condarc), and potentially lockfiles.

Parsing all of these on every TAB press would be wasteful when most
files rarely change between keystrokes. The cache exploits this:

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
| **conda-completion** | **msgpack manifest + Rust binary** | **< 1 ms** (commands/flags) |

## Fuzzy matching

When no prefix or substring match is found for a package name, the
binary falls back to normalized Damerau-Levenshtein similarity. This
handles common typos like transpositions ("nupmy" for "numpy") and
near-misses ("numpie" for "numpy").

Running Damerau-Levenshtein over 28,000+ package names takes about 60 ms.
This is the slowest completion path, but it only fires when no prefix
or substring match exists (i.e., the input is genuinely misspelled).
In practice the delay is barely perceptible.

The matching uses a three-tier strategy to avoid unnecessary work:

1. **Prefix match**: return immediately if any candidates start with the
   query. This is the common case and completes in under 1 ms.
2. **Substring match**: return if any candidates contain the query.
   Still fast, one pass over the candidate list.
3. **Similarity**: only runs when tiers 1 and 2 return nothing. Scores
   are filtered at a 0.6 threshold and capped at 10 results to keep
   output manageable.

## Binary size

The Rust binary is compiled with LTO (link-time optimization), size
optimization (`opt-level = "z"`), and symbol stripping. Dependencies
are kept minimal:

| Dependency | Purpose |
|---|---|
| `serde` + `rmp-serde` | msgpack manifest and cache deserialization |
| `serde` + `toml` | TOML project file parsing (conda.toml, pixi.toml) |
| `serde-saphyr` | YAML parsing (environment.yml, .condarc, lockfiles) |
| `fs-err` | Better I/O errors |

Heavier alternatives were evaluated and rejected:

- **rattler crates** (`rattler_conda_types`, `rattler_lock`): pull in
  nom, regex, simd-json, rayon, purl, fancy-regex. Binary would grow
  from under 1 MB to 5-10 MB with significant startup overhead.
- **clap_complete**: adds clap's full argument parsing framework.
  Unnecessary when the completion engine is custom.
- **serde_yml**: unmaintained, has a RUSTSEC advisory (RUSTSEC-2025-0068).
  Replaced by serde-saphyr (pure Rust, actively maintained).
