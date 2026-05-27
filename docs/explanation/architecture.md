# Architecture

conda-completion uses a hybrid Python/Rust design that splits the work
into two distinct phases: a generation step that runs once, and a
completion step that runs on every TAB press.

## The two-phase design

```{mermaid}
flowchart TD
    subgraph python ["Phase 1: Python (runs once)"]
        direction TB
        A["conda completion generate"] --> B["Call generate_parser()"]
        B --> C["Walk argparse tree"]
        C --> D["Include plugin commands"]
        D --> D2["Resolve package metadata"]
        D2 --> E["Write completion.msgpack\n+ versions.index/store"]
    end

    E --> F[("completion.msgpack\nversions.index/store\n(cache directory)")]

    subgraph rust ["Phase 2: Rust (runs on every TAB)"]
        direction TB
        G["_conda_completer"] --> H["Read completion.msgpack"]
        H --> I["Walk cwd for project context"]
        I --> J["Read global state"]
        J --> K["Prefix/substring/fuzzy match"]
    end

    F --> G

    style python fill:#306998,color:#fff
    style rust fill:#dea584,color:#000
    style F fill:#f5f5f5,stroke:#333
```

**Phase 1: Generation (Python).** `conda completion generate` calls
conda's `generate_parser()` function, which loads all registered plugin
subcommands. The resulting argparse tree is walked recursively to extract
commands, flags, positional arguments, help text, and mutually exclusive
groups. It also resolves package metadata from configured channels via
conda's `SubdirData` API to extract package names and versions, reusing
fresh package metadata when available. The output is a `completion.msgpack`
manifest plus `versions.index` and `versions.store`, all stored in your
platform's cache directory.

**Phase 2: Completion (Rust).** On every TAB press, the shell calls
`_conda_completer`, a statically linked Rust binary. It reads the
manifest, examines the current command line, and outputs matching
candidates in the format your shell expects. No Python process is
started. Package name completion uses a three-tier matching strategy
(prefix, substring, then fuzzy similarity) to handle typos.

## Why this split?

Argparse introspection requires importing `conda` and all its plugins.
That means loading Python, resolving imports, and initializing the plugin
system. This takes hundreds of milliseconds, far too slow for a TAB
press that should feel instant.

By running Python once and caching the result as msgpack, the hot path
becomes a simple binary file read in Rust, with no Python startup cost.

## Plugin awareness

conda's `generate_parser()` function (in `conda.cli.conda_argparse`)
calls `configure_parser_plugins()`, which discovers all registered conda
plugins via entry points and adds their subcommands to the parser tree.
conda-completion introspects the tree *after* this step, so any plugin
that registers `conda_subcommands` is included automatically.

For example, installing `conda-workspaces` adds `workspace`, `ws`, and
`task` subcommands. After running `conda completion generate`, those
subcommands appear in the manifest with full flag and positional
argument details.

### Automatic regeneration

conda-completion registers a `conda_post_commands` hook that fires after
`install`, `remove`, and `update`. The hook hashes the set of registered
plugin entry point names and compares it to the hash stored in the
manifest. If they differ (a plugin was added or removed), the manifest
is regenerated silently.

This means `conda install conda-workspaces` followed by `conda
workspace <TAB>` just works, with no manual regeneration step.

## Contextual completions

Static command trees are not enough. When you type `conda install
--name <TAB>`, you want to see your actual environment names, not a
generic placeholder.

The Rust binary reads project and global files directly:

| Source | What it provides |
| --- | --- |
| `conda.toml` / `pixi.toml` / `pyproject.toml` | Environment names, task names, feature names, channels |
| `environment.yml` | Environment name, channels |
| `anaconda-project.yml` | Environment names, command names |
| `conda-project.yml` | Environment names, command names |
| `conda.lock` / `pixi.lock` | Locked environment names and channels |
| `conda-lock.yml` | Channel names |
| `~/.conda/environments.txt` | All registered environment names |
| `~/.condarc` | Configured channel names |
| `~/.conda/global/global.toml` | Globally installed tool names |

The binary walks upward from the working directory to find project
files (same search order as conda-workspaces) and checks fixed locations
for global state.

## Stat-based file cache

Parsing TOML and YAML on every TAB press would be wasteful when
most files rarely change between keystrokes. The binary maintains a
stat cache (`context_cache.msgpack`) that stores `(mtime, size)` tuples
for every source file.

On each invocation:

1. `stat()` every source file (one syscall each)
2. Compare against cached tuples
3. On a **cache hit** (all stats match): read pre-parsed candidates
   from the cache file. No TOML/YAML parsing at all.
4. On a **cache miss**: re-parse only the changed file(s), merge with
   cached results, and write the updated cache atomically (write to
   `.tmp`, then rename)

This turns the hot path from "parse 5-8 files" into "5-8 stat syscalls
plus one small cache read."

## Shell integration

Each supported shell gets a small script that wires the shell's
completion system to `_conda_completer`. The scripts are generated by
`conda completion init <shell>` and installed into your RC file by
`conda completion install <shell>`.

The scripts differ per shell but follow the same pattern:

1. Define a completion function
2. The function calls `_conda_completer` with the current command line
   state (words and cursor position)
3. Parse the output into the shell's native completion format

The output format varies by shell:

- **bash**: one candidate per line, no descriptions
- **zsh**: `candidate:description` (colon-separated)
- **fish**: `candidate\tdescription` (tab-separated)
- **PowerShell**: `candidate\tdescription` (wrapped in `CompletionResult`)

## Dependency philosophy

The Rust binary uses a minimal set of dependencies:

- `serde` + `rmp-serde` for the msgpack manifest and caches
- `toml` for project files (conda.toml, pixi.toml, pyproject.toml)
- `serde-saphyr` for YAML files (environment.yml, .condarc, lockfiles; pure Rust, no unsafe)
- `fs-err` for better I/O error messages

This keeps the binary small and startup fast. Heavier frameworks like
`clap_complete` or full conda type libraries (rattler) were deliberately
avoided to stay within the performance budget.

## Design decisions

**msgpack over TOML for the manifest.** The manifest is a derived
artifact, never hand-edited. msgpack is smaller and faster to
deserialize than TOML. It is already used in conda's sharded repodata.

**Indexed package-version data.** `completion.msgpack` (~500KB, command
tree plus package names) is always loaded. `versions.index` maps package
names to byte ranges in `versions.store`, and the store record for one
package is loaded only when `=` appears in the current word. This keeps
the common TAB-press fast while avoiding a full version-map
deserialization for one package.

**Argparse introspection over a new hookspec.** Introspecting conda's
existing argparse tree works with all registered plugins immediately.
A dedicated hookspec would require every plugin author to add a new
hook implementation.

**stat() over content hashing.** `stat()` is one syscall per file.
Content hashing requires reading the entire file before deciding
whether to parse it. The only false-negative case (content changes
without mtime/size changing) is vanishingly rare in editing workflows.

**Damerau-Levenshtein over Jaro-Winkler for fuzzy matching.**
Damerau-Levenshtein handles insertions, deletions, substitutions, and
transpositions as single-cost operations. Jaro-Winkler fails on
partial matches where string lengths differ significantly. The
three-tier strategy (prefix > substring > similarity) ensures fuzzy
matching only fires when nothing else matches.
