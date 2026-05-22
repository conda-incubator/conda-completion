# Completer binary

`_conda_completer` is the Rust binary that runs on every TAB press. It
reads the completion manifest and project files to produce candidates.

## Interface

```text
_conda_completer --shell <shell> --manifest <path> [--versions <path>] [--cwd <dir>] -- <words...> <cword>
```

`--shell`
: Output format. One of `bash`, `zsh`, `fish`, `powershell`.

`--manifest`
: Path to the `completion.msgpack` manifest file.

`--versions`
: Path to the `versions.msgpack` file. Defaults to `versions.msgpack` in
  the same directory as the manifest.

`--cwd`
: Working directory to search for project files. Defaults to the current
  directory.

`<words>`
: The current command line split into words.

`<cword>`
: Zero-based index of the word being completed.

## Output formats

### bash

One candidate per line, no descriptions:

```text
install
remove
update
```

### zsh

Colon-separated `candidate:description` format. Colons in descriptions
are escaped:

```text
install:Install a list of packages
remove:Remove a list of packages
update:Update conda packages
```

### fish

Tab-separated `candidate\tdescription`:

```text
install	Install a list of packages
remove	Remove a list of packages
```

### powershell

Tab-separated `candidate\tdescription` (same as fish). The PowerShell
shell script wraps each line in a `CompletionResult` object.

## Project file discovery

The binary walks upward from the working directory looking for project
files in this priority order:

1. `conda.toml`
2. `pixi.toml`
3. `pyproject.toml` (checks `[tool.conda]` and `[tool.pixi]` sections)
4. `anaconda-project.yml`
5. `conda-project.yml`

The first match stops the walk (except that lockfiles are always checked
alongside the matching project file). If no project file is found, the
binary also checks for `environment.yml` at each directory level.

Lockfile supplements (read after a project file match):
- `conda.lock` or `pixi.lock` (rattler-lock format)
- `conda-lock.yml` (conda-lock format)

## Global context

Regardless of project files, the binary always reads:

- `~/.conda/environments.txt` for registered environment names
- `~/.condarc` (and `$CONDARC`) for channel names
- `~/.conda/global/global.toml` for globally installed tool names

## Performance

The stat-based cache (`context_cache.msgpack`) uses `(mtime, size)` tuples
to detect file changes without reading file contents. On a cache hit,
the binary performs one `stat()` syscall per source file and reads the
cached results, avoiding all TOML/YAML parsing.

Cache writes are atomic (write to `.tmp`, then rename) to prevent
corruption if the process is interrupted.
