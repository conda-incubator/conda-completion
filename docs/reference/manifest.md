# Manifest format

The completion manifest (`completion.msgpack`) is the central data structure
that connects the Python introspection step to the Rust completion engine.

The manifest uses msgpack, a compact binary serialization format. Since the
manifest is a derived artifact (never hand-edited), human readability is not
needed. msgpack provides smaller files, faster deserialization, and lower
memory usage compared to TOML. It is also used in conda's sharded repodata
stack.

## Location

The manifest is stored in your platform's cache directory:

| Platform | Path |
| --- | --- |
| Linux | `~/.cache/conda/completion/completion.msgpack` |
| macOS | `~/Library/Caches/conda/completion/completion.msgpack` |
| Windows | `%LOCALAPPDATA%\conda\cache\completion\completion.msgpack` |

A separate `versions.msgpack` file in the same directory stores the mapping
of package names to available versions. It is only loaded when `=` is
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
  channels. Extracted from repodata during `conda completion generate`.
  Used for package name completion in `conda install`, `conda remove`,
  etc.

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

## Versions file

A separate `versions.msgpack` file in the same directory stores the
mapping of package names to their available versions. It is only loaded
by the Rust binary when `=` or `==` is detected in the current word
(e.g., `numpy=<TAB>`).

### Versions schema

The versions file is a msgpack-encoded dict mapping package names
(strings) to sorted lists of version strings:

```json
{
  "numpy": ["1.26.4", "2.0.0", "2.1.0"],
  "pandas": ["2.1.5", "2.2.0", "2.2.1"],
  "scipy": ["1.12.0", "1.13.0", "1.14.0"]
}
```

### Size

The versions file is typically 5-10 MB depending on the number of
configured channels and available versions. It is generated alongside
the main manifest by `conda completion generate`.
