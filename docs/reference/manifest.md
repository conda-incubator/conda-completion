# Manifest format

The completion manifest (`completion.toml`) is the central data structure
that connects the Python introspection step to the Rust completion engine.

## Location

The manifest is stored in your platform's cache directory:

| Platform | Path |
| --- | --- |
| Linux | `~/.cache/conda/completion/completion.toml` |
| macOS | `~/Library/Caches/conda/completion/completion.toml` |
| Windows | `%LOCALAPPDATA%\conda\cache\completion\completion.toml` |

## Schema

```toml
version = 1
generated_at = "2026-01-15T10:30:00+00:00"
plugin_hash = "a1b2c3d4e5f67890"

[root_options."--verbose"]
short = "-v"
description = "Increase verbosity"

[root_options."--json"]
description = "Report as JSON"

[commands.install]
summary = "Install a list of packages"

[commands.install.options."--name"]
short = "-n"
completion_type = "env_name"
description = "Name of environment"
metavar = "ENVIRONMENT"

[commands.install.options."--channel"]
short = "-c"
completion_type = "channel"
description = "Additional channel to search"

[commands.install.options."--dry-run"]
description = "Only display what would have been done"

[commands.workspace]
summary = "Manage project-scoped multi-environment workspaces"

[commands.workspace.subcommands.install]
summary = "Install workspace environments"

[commands.workspace.subcommands.install.options."--environment"]
short = "-e"
completion_type = "env_name"
description = "Target environment"
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
