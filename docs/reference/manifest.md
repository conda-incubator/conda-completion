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
          "metavar": "ENVIRONMENT"
        },
        "--channel": {
          "short": "-c",
          "completion_type": "channel",
          "description": "Additional channel to search"
        }
      }
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
: Dynamic completion type. One of: `env_name`, `channel`, `directory`,
  `package_spec`, `task_name`, `global_tool`.

description
: Help text for the flag.

metavar
: Display name for the value (e.g., `"NAME"`, `"PATH"`).

default
: Default value (informational).

required
: Whether the flag is required.

### PositionalSpec

name
: Argument destination name.

choices
: List of allowed values.

nargs
: Argument count.

completion_type
: Dynamic completion type (same values as OptionSpec).

description
: Help text.

metavar
: Display name for the value.

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
