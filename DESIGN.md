# Plan: `conda-completion` -- Hybrid Python/Rust Shell Completion Plugin

## Context

Conda has no built-in shell completion since 4.4.0 (which used argcomplete). The ecosystem is fragmented across shell-specific, independently maintained projects that are unaware of plugin subcommands (workspace, global, task, spawn, etc.):

**Standalone projects (to be superseded):**
- `tartansandal/conda-bash-completion` -- bash-only, parses help text, on conda-forge
- `conda-incubator/conda-zsh-completion` (originally `esc/conda-zsh-completion`) -- zsh-only, hand-written ~30KB script with 12h package cache
- `tartansandal/mamba-bash-completion` -- bash-only, archived Nov 2024
- `bmcfee/fish-conda` -- fish, unmaintained

**Built into shells/frameworks:**
- Fish shell ships a stale `conda.fish` (based on conda 4.4.11)
- oh-my-bash and Bash-it bundle basic conda completions
- `zchee/zsh-completions` has a `_conda` file

**Cross-shell systems:**
- `sigoden/argc-completions` -- covers conda among 1000+ commands (bash/zsh/fish/PowerShell/Nushell/Elvish), but generic, not conda-aware for dynamic completions

**Precedent from mamba:**
- `mamba`/`micromamba` have built-in `shell completion` commands generating scripts for bash/zsh/fish/PowerShell/xonsh -- same UX pattern we're proposing (note: mamba 2.x is purely C++, does not cover conda's Python plugin commands)

**Current conda docs:** `docs.conda.io/.../enable-tab-completion.html` just points to `conda-bash-completion`.

**Workspace context:** This plugin joins an ecosystem of conda plugins all maintained in the same workspace:
- `conda-workspaces` -- workspace management (`conda workspace`, `conda ws`, `conda task`)
- `conda-global` -- global tool installation (`conda global`)
- `conda-self` -- conda self-management (`conda self install/remove/update`)
- `conda-spawn` -- environment activation in new shells (`conda spawn`)
- `conda-completion` -- shell tab completion (this project)

`conda-completion` will be a hybrid Python/Rust conda plugin (same pattern as `conda-global`) that:
- Introspects conda's full argparse tree (including all plugin subcommands) to generate a msgpack completion manifest
- Ships a tiny Rust binary (`_conda_completer`) that reads the manifest on each TAB press and outputs candidates in <5ms
- Tiered shell support (mirroring conda-spawn's model):
  - **Tier 1** (`shell/`): bash, zsh, PowerShell -- fully tested in CI on every push
  - **Tier 2** (`contrib/`): fish -- best-effort, tested when the shell is installed
- Provides dynamic completions for environment names, channels, and package names via cached msgpack files
- Completes package names from repodata with fuzzy matching (prefix > substring > Damerau-Levenshtein similarity)
- Replaces all of the above with a single, plugin-aware, cross-shell solution
- Custom Rust completion engine (minimal deps: serde + rmp-serde + toml + serde-saphyr + fs-err) rather than clap_complete/argc/gen-completions -- keeps the binary tiny and avoids framework coupling

## Architecture

```
                    ┌──────────────────────────────────┐
                    │  conda completion generate       │  (Python, runs once)
                    │                                  │
                    │  1. Call generate_parser()        │
                    │  2. Walk argparse tree            │
                    │  3. Include plugin commands       │
                    │  4. Fetch repodata via SubdirData │  with progress bar
                    │  5. Extract package names/versions│
                    │  6. Write completion.msgpack      │  commands + package names
                    │  7. Write versions.msgpack        │  name -> version list
                    └────────────┬─────────────────────┘
                                 │
                    ┌────────────▼─────────────────────┐
                    │  <cache_dir>/completion/          │  (platformdirs)
                    │    completion.msgpack              │  commands + package names
                    │    versions.msgpack                │  name -> versions
                    │    context_cache.msgpack           │  stat cache for project files
                    └────────────┬─────────────────────┘
                                 │
                    ┌────────────▼─────────────────────┐
                    │  _conda_completer (Rust)          │  (runs on every TAB)
                    │                                  │
                    │  1. Read completion.msgpack       │  commands + package names
                    │  2. Read versions.msgpack         │  only when '=' detected
                    │  3. Walk cwd for context:         │
                    │     - conda.toml                  │  envs, tasks, features
                    │     - pixi.toml                   │  envs, tasks
                    │     - pyproject.toml              │  [tool.conda.*]
                    │  4. Read global state:            │
                    │     - ~/.conda/global.toml        │  installed tools
                    │     - environments.txt            │  conda environments
                    │     - .condarc                    │  channels
                    │  5. Prefix/substring/fuzzy match  │
                    └──────────────────────────────────┘
```

**Key design choices:**
- **No Python on the hot path.** The Rust binary is the only thing that runs on TAB press. Python only runs during `conda completion generate/install`.
- **Polyglot file walker with stat cache.** The Rust binary reads the ecosystem's native formats directly: TOML for project files, plain text for environments.txt, YAML for .condarc. Parsed results are cached alongside mtime+size stat tuples; files are only re-parsed when their stat changes. Common case (no files changed) is sub-5ms.
- **msgpack manifest format.** The generated command tree and package names are stored in `completion.msgpack`. Version data is in a separate `versions.msgpack`, loaded only when `=` is detected. msgpack was chosen over TOML because the manifest is a derived artifact (never hand-edited), and msgpack offers smaller files, faster deserialization, and lower memory. msgpack is already used in conda's stack (sharded repodata).
- **Two-file split for package data.** `completion.msgpack` (~500KB) is always loaded. `versions.msgpack` (~5-10MB) is loaded only when `=` appears in the current word. This keeps the common TAB-press fast.
- **Three-tier fuzzy matching.** Prefix > substring > normalized Damerau-Levenshtein similarity (the same algorithm rustc/cargo use for "did you mean?" suggestions). Fires only when no prefix or substring match is found.
- **Custom Rust completion engine.** Minimal deps (serde, rmp-serde, toml, serde-saphyr, fs-err), no clap/argc framework dependency. Keeps binary tiny and under our control.
- **Manifest regeneration via `conda_post_commands` hook.** Registers for `install`, `remove`, `update` commands. After these operations, checks if the set of registered plugins has changed (by hashing entry point names) and regenerates the manifest if they differ. This covers the upcoming `conda plugins install/remove/update` commands (conda-self PR #130, issue #124) and the current `conda install/remove` paths. Manual `conda completion generate` is the fallback for edge cases (pip-installed plugins).

**Integration with `conda plugins` (conda-self #124):**
The upcoming `conda plugins` subcommand (Phase 1: PR #130) adds `conda plugins install/remove/update` as dedicated plugin management commands. These are the primary entry points for adding/removing plugins, making them the ideal trigger for manifest regeneration. The `conda_post_commands` hook registers for both the new `plugins` commands and the fallback `install`/`remove` commands.

## Project Structure

```
conda-completion/
├── pyproject.toml                    # hatchling + hatch-vcs
├── Cargo.toml                        # Rust workspace root
├── Cargo.lock
├── AGENTS.md
├── LICENSE
├── README.md
│
├── conda_completion/
│   ├── __init__.py
│   ├── __main__.py                   # `cc` standalone entry point
│   ├── _version.py                   # hatch-vcs generated
│   ├── plugin.py                     # conda plugin hooks (fast import)
│   ├── exceptions.py
│   ├── paths.py                      # manifest/cache path helpers (platformdirs)
│   ├── introspect.py                 # argparse tree walker -> manifest
│   ├── manifest.py                   # manifest dataclasses + msgpack I/O
│   ├── repodata.py                   # extract package names/versions from repodata
│   ├── shell/                        # Tier 1: fully tested in CI
│   │   ├── __init__.py               # base Shell class + registry
│   │   ├── bash.py                   # bash completion script template
│   │   ├── zsh.py                    # zsh completion script template
│   │   └── powershell.py             # PowerShell completion script template
│   ├── contrib/                      # Tier 2: best-effort, tested when shell available
│   │   ├── __init__.py
│   │   └── fish.py                   # fish completion script template
│   └── cli/
│       ├── __init__.py
│       ├── main.py                   # parser config + dispatch
│       ├── generate.py               # `conda completion generate`
│       ├── install.py                # `conda completion install <shell>`
│       ├── uninstall.py              # `conda completion uninstall <shell>`
│       └── init.py                   # `conda completion init <shell>` (print script)
│
├── packages/
│   └── conda-completer/
│       ├── Cargo.toml                # binary crate: _conda_completer
│       ├── pyproject.toml            # maturin build
│       ├── python/
│       │   └── conda_completer/
│       │       └── __init__.py       # find_completer_binary()
│       └── src/
│           ├── main.rs               # entry point: parse args, dispatch
│           ├── manifest.rs           # msgpack command tree deserialization
│           ├── context.rs            # project context: walk cwd for workspace/project files
│           │                         #   conda.toml, pixi.toml, pyproject.toml (TOML)
│           │                         #   environment.yml, anaconda-project.yml, conda-project.yml (YAML)
│           │                         #   conda.lock, conda-lock.yml (lockfiles)
│           ├── global.rs             # global context: global.toml, environments.txt, .condarc
│           ├── cache.rs              # mtime+size stat cache for parsed file results
│           ├── matcher.rs            # prefix/substring/fuzzy matching
│           ├── similarity.rs         # Damerau-Levenshtein distance
│           └── shell.rs              # shell-specific output formatting
│
├── tests/
│   ├── conftest.py
│   ├── test_introspect.py
│   ├── test_manifest.py
│   ├── cli/
│   │   ├── conftest.py
│   │   ├── test_generate.py
│   │   └── test_install.py
│   └── test_completer.py            # integration: invoke Rust binary with sample files
│
└── recipe/
    └── recipe.yaml                   # multi-output conda-forge recipe
```

## Implementation Phases

### Phase 1: Project Scaffolding

Create the project skeleton following conda-global's exact pattern.

**Files to create:**
- `pyproject.toml` -- modeled on `/Users/jezdez/Code/git/conda-global/pyproject.toml`
  - Build: hatchling + hatch-vcs
  - Entry points: `[project.entry-points.conda] "conda-completion" = "conda_completion.plugin"`
  - Script: `cc = "conda_completion.__main__:main"`
  - Deps: `conda >=25.1`, `conda-completer`, `platformdirs >=4.0`, `msgpack >=1.0`
  - Pixi workspace with rust toolchain, dev/test/docs envs
- `Cargo.toml` -- workspace root, same release profile as conda-global (LTO fat, opt-level z, strip)
- `packages/conda-completer/Cargo.toml` -- binary `_conda_completer`, deps: serde, rmp-serde, toml, serde-saphyr, fs-err
- `packages/conda-completer/pyproject.toml` -- maturin config, same pattern as conda-trampoline
- `conda_completion/__init__.py`, `_version.py`, `__main__.py`, `exceptions.py`
- `AGENTS.md` -- coding guidelines adapted from both conda (`/Users/jezdez/Code/git/conda/AGENTS.md`) and conda-workspaces (`/Users/jezdez/Code/git/conda-workspaces/AGENTS.md`). Combine:
  - From conda: local dev setup, Ruff formatting/linting, test patterns (clear names, small focused tests, pytest fixtures)
  - From conda-workspaces: project structure, import conventions (relative intra-package, inline only for perf-critical), typing (`str | None`, `from __future__ import annotations`, `ty`), no mock library (pytest natives only), CLI architecture, documentation standards, PR description conventions, plugin design patterns
  - Add Rust-specific sections: `cargo fmt`/`clippy` enforcement, minimal dependency philosophy, binary size targets

### Phase 2: Plugin Registration + CLI Framework

**`conda_completion/plugin.py`:**
```python
@hookimpl
def conda_subcommands():
    from .cli.main import configure_parser, execute
    yield CondaSubcommand(
        name="completion",
        summary="Generate and install shell tab completions for conda.",
        action=execute,
        configure_parser=configure_parser,
    )

@hookimpl
def conda_post_commands():
    from conda.plugins.types import CondaPostCommand
    yield CondaPostCommand(
        name="conda-completion-regen",
        action=_maybe_regenerate,
        run_for={"install", "remove", "update"},
    )
```

The `_maybe_regenerate` hook checks if the set of registered plugin entry points has changed since the last manifest generation (by comparing a hash stored alongside the manifest). If changed, it regenerates the manifest. This covers `conda self install <plugin>`, `conda install <plugin>`, and `conda remove <plugin>`.

**`conda_completion/cli/main.py`:**
- Subcommands: `generate`, `install`, `uninstall`, `init`
- `generate` -- introspect conda parser, write manifest + caches
- `install <shell>` -- generate + write shell RC hook (with confirmation)
- `uninstall <shell>` -- remove the RC hook
- `init <shell>` -- print the shell script to stdout (for `eval "$(conda completion init bash)"`)

### Phase 3: Argparse Introspection + Manifest Generation

**`conda_completion/introspect.py`** -- the core logic:

1. Call `conda.cli.conda_argparse.generate_parser()` to get the full argparse tree with all plugins configured (this calls `configure_parser_plugins()` at `conda_argparse.py:277` which registers all plugin subcommands -- workspace, global, self, spawn, task, etc.)
2. Recursively walk the parser tree using the same internal API conda uses: `parser._subparsers._group_actions[0].choices` (see `conda_argparse.py:198` `find_builtin_commands()`)
3. For each parser node, extract all metadata argparse provides:
   - **Optional arguments (flags)**: name, short form, choices, nargs, help text, metavar, default, required
   - **Positional arguments**: name, nargs, choices, help text, metavar
   - **Subcommands**: name, help/summary text (recurse into each)
   - **Mutually exclusive groups**: which flags conflict with each other
   - **Metavar/type hints**: e.g. `NAME`, `PATH`, `URL` -- signals what kind of value is expected
4. Apply a heuristic type map to annotate dynamic completion types:
   - `--name`/`-n` -> `env_name`
   - `--environment`/`-e` -> `env_name`
   - `--channel`/`-c` -> `channel`
   - `--prefix`/`-p` -> `directory`
   - positionals named `package`/`packages` -> `package_spec`

Shells that support descriptions (zsh, fish, PowerShell) will show help text alongside candidates. For example, `conda <TAB>` in zsh would display:

```text
install    -- Install packages into an environment
workspace  -- Manage project-scoped multi-environment workspaces
global     -- Install and manage globally available CLI tools
spawn      -- Activate conda environments in new shells
```

And `conda install --<TAB>` would show:

```text
--name       -- Name of environment
--channel    -- Additional channel to search for packages
--dry-run    -- Only display what would have been done
--force-reinstall -- Ensure that any user-requested package...
```

**`conda_completion/manifest.py`** -- data model:

```python
@dataclass(frozen=True)
class CompletionManifest:
    version: int
    generated_at: str
    plugin_hash: str          # hash of registered plugin names for staleness detection
    commands: dict[str, CommandSpec]
    dynamic_sources: dict[str, DynamicSource]

@dataclass(frozen=True)
class CommandSpec:
    summary: str | None
    options: dict[str, OptionSpec]
    positionals: list[PositionalSpec]
    subcommands: dict[str, CommandSpec]
    exclusive_groups: list[list[str]]  # e.g. [["--from-lockfile", "--from-prefix"]]

@dataclass(frozen=True)
class OptionSpec:
    short: str | None         # e.g. "-n"
    choices: list[str] | None
    nargs: str | int | None
    completion_type: str | None  # e.g. "env_name", "channel", "directory"
    description: str | None   # help text, shown in zsh/fish/PowerShell
    metavar: str | None       # e.g. "NAME", "PATH" -- type hint for the value
    default: str | None       # default value if flag is omitted
    required: bool

@dataclass(frozen=True)
class DynamicSource:
    cache_file: str
    ttl_seconds: int
```

Output location: `platformdirs.user_cache_dir("conda") / "completion" / "completion.msgpack"`

- Linux: `~/.cache/conda/completion/completion.msgpack`
- macOS: `~/Library/Caches/conda/completion/completion.msgpack`
- Windows: `%LOCALAPPDATA%\conda\cache\completion\completion.msgpack`

This follows the same pattern as conda's notices cache (`conda/notices/cache.py:73-79`). The data is regenerated, not user-authored, so it belongs in the cache directory.

### Phase 4: Rust Completer Binary

**`packages/conda-completer/src/main.rs`:**

Interface: `_conda_completer --shell <shell> --manifest <path> -- <words...> <cword>`

Algorithm:
1. Parse CLI args to get shell type, manifest path, current words, cursor word index
2. Deserialize `completion.msgpack` into Rust structs (serde + rmp-serde crate)
3. Walk the command tree following the words to find current context
4. Determine what to complete:
   - If expecting a subcommand, list matching subcommand names
   - If expecting a flag, list matching `--` options with descriptions
   - If mid-flag-value with `choices`, filter choices
   - If mid-flag-value with a `completion_type`, resolve via contextual file walking (see below)
5. Apply prefix filtering
6. Output in shell-specific format:
   - Bash: one candidate per line
   - Zsh: `candidate:description` format
   - Fish: `candidate\tdescription` format
   - PowerShell: `CompletionResult` format

**Contextual file walking (`context.rs` + `global.rs`):**

The Rust binary reads project and global state directly from native ecosystem files. No intermediate caches for project data -- the source of truth is the completion source. Only lightweight serde structs are needed (no full schema validation).

| Format | Files | What we extract |
| ------ | ----- | --------------- |
| TOML | `conda.toml` | env names (`[environments]` keys), task names (`[tasks]` keys), feature names (`[feature.*]` keys), channel names |
| TOML | `pixi.toml` | env names, task names, features, channels (same structure) |
| TOML | `pyproject.toml` | env/task/feature names from `[tool.conda.*]` or `[tool.pixi.*]` sections |
| TOML | `~/.conda/global.toml` | globally installed tool names |
| YAML | `environment.yml` | env name (`name:`), dependency names (`dependencies:`) |
| YAML | `anaconda-project.yml` | env names (`env_specs:` keys), command names (`commands:` keys) |
| YAML | `conda-project.yml` | env names, command names |
| YAML | `.condarc` | channel names (`channels:`), env dirs |
| JSON | `conda.lock` | env names, locked package names per env (rattler-lock v6 format with `version: 1` byte) |
| text | `~/.conda/environments.txt` | registered environment paths (one per line) |

The binary walks upward from cwd to find project files (same search order as conda-workspaces: conda.toml > pixi.toml > pyproject.toml, then legacy YAML formats). Global files are read from fixed locations via `platformdirs`.

**Dependencies** (minimal, like conda-trampoline):

- `serde` -- serialization framework
- `rmp-serde` -- completion.msgpack manifest and cache deserialization
- `toml` -- conda.toml/pixi.toml/pyproject.toml project file parsing
- `serde-saphyr` -- environment.yml, anaconda-project.yml, conda-project.yml, .condarc parsing
- `fs-err` -- better I/O errors

**Why not rattler crates?** `rattler_conda_types` pulls in nom, regex, simd-json, rayon, purl, fancy-regex; `rattler_lock` adds rattler_solve, pep508_rs, pep440_rs, xxhash. The binary would go from <1.5MB to 5-10MB and startup from <10ms to ~50ms. For completion, we don't need full schema validation or version solving -- just extracting string lists (env names, task names, package names) from known TOML/YAML paths. A few serde structs per format is sufficient.

**Stat-based file cache:**

The completer avoids re-parsing files that haven't changed between TAB presses using an mtime+size stat cache:

1. On each invocation, `stat()` every source file (manifest, project files, global files) -- one syscall each, ~0.1ms total
2. Compare `(path, mtime, size)` tuples against a cached index stored in `context_cache.msgpack`
3. **Cache hit** (common case): all stats match, deserialize pre-parsed candidates from the cache file (~1ms). No TOML/YAML parsing at all.
4. **Cache miss**: re-parse only the file(s) whose mtime/size changed, merge with cached results for unchanged files, write updated cache

Cache location: `<cache_dir>/completion/context_cache.msgpack` (alongside the manifest). The cache stores the extracted string lists (env names, task names, channel names, etc.) keyed by source file path, plus the stat tuples for invalidation.

This turns the hot path from "parse 5-8 files" into "5-8 stat syscalls + one small cache read" -- sub-5ms on cache hit. Content hashing is unnecessary; `stat()` is cheaper and sufficient for detecting edits.

**Performance target**: <5ms on cache hit, <15ms on cache miss (re-parse changed files).

### Phase 6: Shell Integration Scripts

Tiered shell support mirroring conda-spawn's model:

- **Tier 1** (`conda_completion/shell/`): bash, zsh, PowerShell -- fully tested in CI on every push, actively maintained. PowerShell is Tier 1 because a great Windows experience is critical for conda.
- **Tier 2** (`conda_completion/contrib/`): fish -- best-effort, tested only when the shell binary is installed, relies on user reports for catching shell-specific bugs

Each shell module generates a script that:
1. Defines a completion function
2. The function invokes `_conda_completer` with the current command line state
3. Parses the output into the shell's completion system

`shell/__init__.py` provides a base `Shell` class and a registry mapping shell names to implementations (combining both tiers), similar to conda-spawn's `registry.py`.

**Tier 1 -- Bash** (`shell/bash.py`):
```bash
_conda_completion() {
    local completer="{completer_path}"
    local manifest="{manifest_path}"
    COMPREPLY=( $("$completer" --shell bash --manifest "$manifest" -- "${COMP_WORDS[@]}" "$COMP_CWORD" 2>/dev/null) )
}
complete -o default -F _conda_completion conda
```

**Tier 1 -- Zsh** (`shell/zsh.py`):
```zsh
#compdef conda
_conda() {
    local -a completions
    completions=("${(@f)$({completer_path} --shell zsh --manifest {manifest_path} -- "${words[@]}" $CURRENT 2>/dev/null)}")
    _describe 'conda' completions
}
```

**Tier 1 -- PowerShell** (`shell/powershell.py`):

```powershell
Register-ArgumentCompleter -Native -CommandName conda -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    & "{completer_path}" --shell powershell --manifest "{manifest_path}" -- $commandAst.ToString().Split() $cursorPosition |
        ForEach-Object { [System.Management.Automation.CompletionResult]::new($_) }
}
```

**Tier 2 -- Fish** (`contrib/fish.py`):

```fish
complete -c conda -a '({completer_path} --shell fish --manifest {manifest_path} -- (commandline -cop) (commandline -t) 2>/dev/null)'
```

### Phase 7: Install/Uninstall Commands

**`conda completion install <shell>`:**
1. Detect shell if not specified (from `$SHELL`)
2. Run `generate` to ensure manifest + caches exist
3. Determine RC file (`.bashrc`, `.zshrc`, `config.fish`, `$PROFILE`)
4. Show the line to add, require `--yes` or interactive confirmation
5. Write a delimited block:
   ```
   # >>> conda-completion >>>
   eval "$(/path/to/conda completion init bash)"
   # <<< conda-completion <<<
   ```
6. `--dry-run` mode to preview without writing

**`conda completion uninstall <shell>`:**
- Find and remove the delimited block from the RC file

### Phase 8: Documentation (Diataxis + VHS Demos)

Full documentation following the conda-workspaces pattern: Sphinx + MyST with conda_sphinx_theme, Diataxis framework coverage, VHS demo recordings, and migration guides for every predecessor.

**Docs structure:**

```text
docs/
├── conf.py                           # Sphinx config (conda_sphinx_theme, myst_parser,
│                                     # sphinx_design, sphinx_copybutton, sphinxarg.ext)
├── index.md                          # Landing page with install tabs, demo GIF, nav cards
├── quickstart.md                     # 5-minute setup (install, generate, init, test)
│
├── tutorials/
│   ├── index.md                      # Tutorials hub
│   ├── setup-bash.md                 # Bash completion end-to-end
│   ├── setup-zsh.md                  # Zsh completion end-to-end
│   ├── setup-powershell.md           # PowerShell completion end-to-end
│   ├── setup-fish.md                 # Fish completion end-to-end
│   ├── plugin-completions.md         # How plugin subcommands auto-complete
│   └── coming-from/
│       ├── index.md                  # Migration hub with grid cards
│       ├── conda-bash-completion.md  # From tartansandal/conda-bash-completion
│       ├── conda-zsh-completion.md   # From conda-incubator/conda-zsh-completion
│       ├── fish-conda.md             # From bmcfee/fish-conda
│       ├── argc-completions.md       # From sigoden/argc-completions (conda entry)
│       └── builtin-shells.md         # From oh-my-bash, Bash-it, fish built-in conda.fish
│
├── reference/
│   ├── cli.md                        # Auto-generated CLI reference (sphinxarg.ext)
│   ├── manifest.md                   # completion.msgpack schema reference
│   ├── api.md                        # Python API reference hub
│   ├── api/
│   │   ├── introspect.md             # Argparse introspection API
│   │   ├── manifest.md               # Manifest dataclasses
│   │   └── cache.md                  # Cache management API
│   ├── shell-support.md              # Shell support matrix (Tier 1/2, features per shell)
│   └── completer-binary.md           # _conda_completer interface, args, output formats
│
├── explanation/
│   ├── motivation.md                 # Why conda-completion exists, landscape comparison
│   ├── architecture.md               # Hybrid Python/Rust design, manifest-based approach
│   ├── performance.md                # Why Rust, benchmarks vs argcomplete/help-parsing
│   └── faq.md                        # Common questions
│
└── _static/
    └── css/custom.css
```

**Diataxis coverage:**

| Quadrant | Content |
|----------|---------|
| **Tutorials** | Quickstart, per-shell setup guides, plugin completion walkthrough, migration guides |
| **How-to** | Embedded in tutorials (setup-*.md) and migration guides (coming-from/*) |
| **Reference** | CLI (auto-generated), manifest schema, API docs, shell support matrix, completer binary spec |
| **Explanation** | Motivation/landscape, architecture, performance rationale, FAQ |

**Migration guides (`coming-from/`):**

Each guide follows the same structure:

1. What the old tool does and how it works
2. Side-by-side comparison (old setup vs new setup)
3. Step-by-step migration instructions (uninstall old, install new)
4. What you gain (plugin awareness, cross-shell, dynamic completions, descriptions)
5. Known differences or limitations

| Guide | Source project | Key conversion steps |
| ----- | -------------- | -------------------- |
| `conda-bash-completion.md` | `tartansandal/conda-bash-completion` | Remove from `.bashrc`, `conda remove conda-bash-completion`, install conda-completion |
| `conda-zsh-completion.md` | `conda-incubator/conda-zsh-completion` | Remove `$fpath` entry or oh-my-zsh plugin, install conda-completion |
| `fish-conda.md` | `bmcfee/fish-conda` | Remove Fish plugin, install conda-completion |
| `argc-completions.md` | `sigoden/argc-completions` | Remove conda entry from argc config, install conda-completion |
| `builtin-shells.md` | oh-my-bash, Bash-it, Fish built-in | Remove framework plugin/completion, install conda-completion |

**VHS demos (`demos/`):**

```text
demos/
├── _settings.tape                    # Shared VHS settings (font, theme, env vars)
├── quickstart.tape                   # Install + generate + init + first TAB
├── subcommand-completion.tape        # Completing conda subcommands with descriptions
├── option-completion.tape            # Completing --flags with help text
├── dynamic-completion.tape           # Completing env names, package names
├── plugin-completion.tape            # Completing plugin subcommands (workspace, global, spawn)
├── install.tape                      # conda completion install bash (RC file setup)
└── migration.tape                    # Removing old completion, installing new one
```

Each tape produces `.gif` (embedded in docs) and `.mp4` (higher quality). GIFs are embedded in markdown via:

```markdown
![quickstart demo](../demos/quickstart.gif)
```

`conf.py` includes `html_extra_path = ["../demos"]` to copy demos into the built HTML.

**Pixi task for recording:**

```toml
[tool.pixi.tasks.demos]
cmd = """bash -c 'if [ -n "$1" ]; then vhs "demos/$1.tape"; else for tape in demos/*.tape; do [[ "$(basename "$tape")" == _* ]] && continue; vhs "$tape"; done; fi' -- {{ name }}"""
args = [{ arg = "name", default = "" }]
description = "Record demo GIFs"
```

### Phase 9: Tests

- `test_introspect.py` -- build minimal argparse trees, verify walker produces correct manifest structures; parametrize over: nested subcommands, flags with choices, positionals, greedy plugin parsers
- `test_manifest.py` -- round-trip msgpack serialization, version field, schema invariants
- `test_install.py` -- install writes correct block, uninstall removes it, idempotent
- `test_completer.py` -- invoke `_conda_completer` as subprocess with sample completion.msgpack + project files (conda.toml, environment.yml, conda.lock), verify contextual completions per shell

## Key Reference Files

| Purpose | File |
|---------|------|
| Project template | `/Users/jezdez/Code/git/conda-global/pyproject.toml` |
| Cargo workspace | `/Users/jezdez/Code/git/conda-global/Cargo.toml` |
| Rust binary crate | `/Users/jezdez/Code/git/conda-global/packages/conda-trampoline/Cargo.toml` |
| Maturin config | `/Users/jezdez/Code/git/conda-global/packages/conda-trampoline/pyproject.toml` |
| Rust binary example | `/Users/jezdez/Code/git/conda-global/packages/conda-trampoline/src/main.rs` |
| Plugin pattern | `/Users/jezdez/Code/git/conda-global/conda_global/plugin.py` |
| Spawn plugin pattern | `/Users/jezdez/Code/git/conda-spawn/conda_spawn/plugin.py` |
| Self plugin install | `/Users/jezdez/Code/git/conda-self/conda_self/cli/main_install.py` |
| `conda plugins` PR | conda-incubator/conda-self PR #130, issue #124 (adds `conda plugins list/install/remove/update`) |
| Argparse tree builder | `/Users/jezdez/Code/git/conda/conda/cli/conda_argparse.py` (generate_parser L124, configure_parser_plugins L277, find_builtin_commands L195) |
| `conda commands` | `/Users/jezdez/Code/git/conda/conda/cli/main_commands.py` (existing completion helper) |
| AGENTS.md (conda) | `/Users/jezdez/Code/git/conda/AGENTS.md` (dev setup, Ruff, CalVer, deprecations, test patterns) |
| AGENTS.md (workspaces) | `/Users/jezdez/Code/git/conda-workspaces/AGENTS.md` (imports, typing, no-mock, CLI arch, plugin design) |

## Design Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Rust completion engine | Custom (serde + rmp-serde + toml + serde-saphyr + fs-err) | Keeps binary tiny (<1.5MB). Rattler crates (nom, regex, simd-json, rayon) would balloon to 5-10MB. We only need to extract string lists from known file paths, not full schema validation |
| Manifest format | msgpack | Derived artifact, never hand-edited. Smaller files, faster deserialization, lower memory than TOML. Already used in conda's sharded repodata stack |
| Package data split | Two files: completion.msgpack + versions.msgpack | completion.msgpack (~500KB) is always loaded. versions.msgpack (~5-10MB) is loaded only on `=` detection. Keeps common TAB-press fast |
| Fuzzy matching | Three-tier: prefix > substring > normalized Damerau-Levenshtein | Prefix/substring cover exact use; similarity fires only on typos. Damerau-Levenshtein handles insertions, deletions, substitutions, and transpositions (what rustc/cargo use). Jaro-Winkler was rejected because it fails on partial matches |
| Manifest staleness | `conda_post_commands` hook | Covers `conda plugins install/remove/update` (PR #130), `conda install`, `conda remove`. Fallback: manual `conda completion generate` for pip-installed plugins |
| Scope | conda only | mamba 2.x is purely C++ with its own completion. We complete conda + all its Python plugins |
| Shell support | Tier 1: bash, zsh, PowerShell; Tier 2: fish | Mirrors conda-spawn's tiered model. PowerShell is Tier 1 because Windows is critical for conda |
| Argparse introspection vs new hookspec | Introspection | Works immediately with all existing plugins without requiring them to opt in |
| File caching | mtime+size stat cache | Avoids re-parsing unchanged files on every TAB press. `stat()` is one syscall per file (~0.1ms total); content hashing would require reading the file first, defeating the purpose. Sub-5ms on cache hit vs ~15ms without |
| AGENTS.md | Adapted from conda + conda-workspaces | Combines conda's release/deprecation/test conventions with conda-workspaces' stricter no-mock, import, typing, and CLI architecture rules. Adds Rust-specific sections |

## Verification

1. **Unit tests**: `pixi run test` -- all introspection, manifest tests pass
2. **Rust binary**: `cargo build --release` compiles, `cargo test` passes, binary is <1.5MB
3. **Generate**: `conda completion generate` produces valid `completion.msgpack` that includes built-in commands + all plugin subcommands (workspace, ws, global, self, spawn, task, completion)
4. **Init**: `conda completion init bash` prints a valid bash completion script
5. **End-to-end**: Source the generated script, type `conda inst<TAB>` -> completes to `install`; `conda workspace <TAB>` -> lists workspace subcommands; `conda install --name <TAB>` -> lists environment names; `conda spawn <TAB>` -> completes spawn options
6. **Contextual completions**: In a directory with conda.toml, `conda workspace install -e <TAB>` -> lists environment names from the manifest; `conda task run <TAB>` -> lists task names; in a directory with environment.yml, `conda install --name <TAB>` -> shows the env name from the YAML
7. **Performance**: Time `_conda_completer` invocation -- should be <20ms
8. **Post-command regen**: Install a plugin via `conda self install`, verify manifest is automatically regenerated with new subcommands

## Post-plan: Store in repo

After implementation, copy this plan to `/Users/jezdez/Code/git/conda-completion/DESIGN.md` so the design rationale and decisions are preserved alongside the code (matching conda-workspaces' `DESIGN.md` pattern).
