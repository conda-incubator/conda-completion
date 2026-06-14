# Manifest format

The completion manifest (`completion.msgpack`) connects the Python
introspection step to the Rust completion engine. It uses msgpack, a
compact binary format also used in conda's sharded repodata stack.

## Location

The manifest is stored in your platform's cache directory:

| Platform | Path |
| --- | --- |
| Linux | `~/.cache/conda/completion/completion.msgpack` |
| macOS | `~/Library/Caches/conda/completion/completion.msgpack` |
| Windows | `%LOCALAPPDATA%\conda\cache\completion\completion.msgpack` |

Pass `conda completion --cache-dir PATH` or set
`CONDA_COMPLETION_CACHE_DIR` to override the directory that contains the
manifest and related cache files.

Package versions are stored in two files in the same directory:
`versions.index` and `versions.store`. They are only loaded when `=` is
detected in the current word (e.g., `numpy=<TAB>`).

## Schema

The manifest is a msgpack-encoded dict with these top-level keys. Shown
here as equivalent JSON for readability:

```json
{
  "version": 1,
  "generated_at": "2026-01-15T10:30:00+00:00",
  "plugin_hash": "a1b2c3d4e5f67890",
  "package_names": ["numpy", "pandas", "scipy", "..."],
  "root_options": {
    "--verbose": {"short": "-v", "description": "Increase verbosity"},
    "--json": {"description": "Report as JSON"}
  },
  "commands": {
    "install": {
      "summary": "Install a list of packages",
      "options": {
        "--name": {
          "short": "-n",
          "completion_type": "env_name",
          "description": "Name of environment",
          "metavar": "ENVIRONMENT",
          "group": "Target Environment Specification"
        },
        "--channel": {
          "short": "-c",
          "completion_type": "channel",
          "description": "Additional channel to search"
        }
      }
    }
  },
  "aliases": {
    "cx": {"target": ["exec"]}
  },
  "runtime_sources": {
    "cached_tool": {
      "kind": "directory_entries",
      "description": "cached tool",
      "group": "tool",
      "home_suffix": [".conda", "global", "tools"],
      "entry_type": "directory",
      "max_entries": 10000
    }
  }
}
```

## Field reference

### Root fields

version
: Schema version. Currently `1`.

generated_at
: ISO 8601 timestamp of when the manifest was generated.

plugin_hash
: A hex string hashing the set of registered plugin entry point names.
  Used to detect when plugins have been added or removed.

package_names
: Deduplicated, sorted list of all package names across configured
  channels when repodata is included during `conda completion generate`.
  Used for package name completion in `conda install`, `conda remove`,
  etc. Omitted when generation runs with `--no-repodata`.

aliases
: Map of executable names to command paths. Shell integrations register
  the same completion function for each alias, and the Rust completer
  normalizes the alias back to the target command path before matching.

runtime_sources
: Map of plugin-defined runtime candidate sources. Runtime sources are
  resolved by the Rust binary on TAB without importing Python.

### CommandSpec

summary
: Help text for the command (shown in zsh/fish/PowerShell completions).

options
: Map of flag names to OptionSpec objects (keyed by long form,
  e.g., `"--name"`).

positionals
: List of positional argument specs.

subcommands
: Nested map of subcommand names to CommandSpec objects.

exclusive_groups
: List of lists of mutually exclusive flag names.

### OptionSpec

short
: Short flag form (e.g., `"-n"`).

choices
: List of allowed values (static completion).

nargs
: Argument count (`"0"`, `"1"`, `"?"`, `"*"`, `"+"`).

completion_type
: Dynamic completion type. Built-in values are `env_name`,
  `environment`, `channel`, `directory`, `file`, `path`, `package_spec`,
  `task_name`, and `global_tool`. Plugin-defined values can reference
  entries in `runtime_sources`.

description
: Help text for the flag.

metavar
: Display name for the value (e.g., `"NAME"`, `"PATH"`).

default
: Default value (informational).

required
: Whether the flag is required.

group
: Argparse action group title, when conda or a plugin provides one.
  The zsh integration uses it to keep related candidates together.

### PositionalSpec

name
: Argument destination name.

choices
: List of allowed values.

nargs
: Argument count.

completion_type
: Dynamic completion type (same values as OptionSpec).

completion
: Compound completion metadata with a default list of sources and
  optional context-sensitive rules. Each rule can replace the source list
  when all of its `when_options` flags have already been used.

description
: Help text.

metavar
: Display name for the value.

### CompletionSpec

sources
: Dynamic completion source names used by default.

rules
: Ordered list of CompletionRule objects. The first rule whose
  `when_options` are all present determines the sources for that
  completion.

### CompletionRule

sources
: Dynamic completion source names to use when the rule matches.

when_options
: Flag names that must have appeared earlier on the command line.

### AliasSpec

target
: Command path to prepend when the executable alias is used. For
  example, `{"target": ["exec"]}` lets `cx run` complete like
  `conda exec run`.

description
: Optional human-readable description.

### RuntimeSourceSpec

kind
: Runtime source implementation. Currently `directory_entries`.

description
: Description shown alongside candidates in shells that support it.

group
: Candidate group name used by shell integrations that support grouping.

env_var
: Environment variable that can point at the source root.

env_suffix
: Path segments appended to `env_var` when it is set.

home_suffix
: Path segments appended to the user's home directory when `env_var` is
  not set.

entry_type
: Entry filter. One of `directory`, `file`, or `any`.

strip_suffix
: Optional delimiter used to strip encoded suffixes from directory entry
  names.

max_entries
: Maximum number of entries read from the source directory, capped by the
  Rust completer's internal limit.

## Version files

The version cache uses an indexed msgpack store:

`versions.index`
: A msgpack-encoded dict mapping package names to `(offset, length)`
  records in `versions.store`.

`versions.store`
: A byte store containing one msgpack-encoded version list per package.

The completion engine only loads these files when `=` or `==` is
detected in the current word (e.g., `numpy=<TAB>`). Normal package name
completion reads only `completion.msgpack`.

Shown as equivalent JSON, the index looks like:

```json
{
  "numpy": [0, 24],
  "pandas": [24, 29]
}
```

Each referenced store record is a msgpack-encoded list such as
`["2.1.0", "2.0.0", "1.26.4"]`. This avoids deserializing the full
package-to-version mapping for a single version lookup while preserving
the simple msgpack format.
