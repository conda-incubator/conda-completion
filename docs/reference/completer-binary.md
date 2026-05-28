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
: Path to the `versions.index` file. Defaults to `versions.index` in
  the same directory as the manifest. The matching `versions.store`
  file is expected next to the index.

`--cwd`
: Working directory to search for project files. Defaults to the current
  directory.

`<words>`
: The current command line split into words by the shell integration.
  PowerShell uses command AST elements so quoted paths and arguments
  stay intact.

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

Tab-separated `group<TAB>candidate:description` format. Colons in
descriptions are escaped:

```text
subcommand	install:Install a list of packages
subcommand	remove:Remove a list of packages
subcommand	update:Update conda packages
```

When directory fallback is needed, the binary emits the sentinel
`__dir__`; the zsh shell function then delegates to `_path_files -/`.

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

The first match stops the walk (except that lockfiles are also checked
alongside the matching project file). If no project file is found, the
binary also checks for `environment.yml` at each directory level.

Lockfile supplements (read after a project file match):
- `conda.lock` or `pixi.lock` (rattler-lock format)
- `conda-lock.yml` (conda-lock format)

`conda.toml` is supported because
[conda-workspaces](https://github.com/conda-incubator/conda-workspaces)
uses it as an emerging workspace manifest. It should not be read as a
formal conda standard.

Discovery stops at common VCS roots such as `.git`, `.hg`, and `.svn`,
and the upward walk has a fixed maximum depth to avoid expensive scans
from deep or unusual working directories.

## Global context

Regardless of project files, the binary checks these user-level files:

- `~/.conda/environments.txt` for registered environment names
- `~/.condarc` (and `$CONDARC`) for channel names
- `~/.conda/global/global.toml` for globally installed tool names used
  by arguments explicitly marked as `global_tool`

For channel names, `$CONDARC` is read in addition to `~/.condarc` when it
points at a regular file. On Windows, the system-level
`C:\ProgramData\conda\.condarc` is also checked when present.

## Performance

The stat-based cache (`context_cache.msgpack`) uses `(mtime, size)` tuples
to detect file changes without reading file contents. On a cache hit,
the binary performs one `stat()` syscall per source file and reads the
cached results, avoiding all TOML/YAML parsing.

Cache writes are atomic (write to `.tmp`, then rename) to prevent
corruption if the process is interrupted.
