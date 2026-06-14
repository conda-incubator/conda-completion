# Plugin completions

How conda-completion discovers your plugin's subcommands, and how to
make your plugin work well with it.

Conda documents the subcommand plugin hook in its
{external+conda:doc}`plugin subcommands guide <dev-guide/plugins/subcommands>`.

## Discovery

conda-completion calls conda's `generate_parser()` to walk the full
argparse tree, including all plugin-registered subcommands. If your
plugin uses the {external+conda:doc}`conda_subcommands
<dev-guide/plugins/subcommands>` hook with a `configure_parser` callback,
your flags, positionals, and subcommands are included the next time the
manifest is generated. No conda-completion-specific configuration is
needed.

## Making your plugin completion-friendly

### Help text

conda-completion extracts the `help` argument from every flag and
positional. Shells that support descriptions (zsh, fish, PowerShell)
show this text alongside candidates:

```python
parser.add_argument(
    "--environment", "-e",
    help="Target environment name",
    metavar="NAME",
)
```

### Metavar for value hints

`metavar` tells users what kind of value a flag expects:

```python
parser.add_argument(
    "--prefix",
    help="Full path to environment location",
    metavar="PATH",
)
```

### Subcommands

Use argparse subparsers for nested completion. The system walks the
tree recursively:

```python
def configure_parser(parser):
    sub = parser.add_subparsers(dest="subcmd")
    p_list = sub.add_parser("list", help="List items")
    p_run = sub.add_parser("run", help="Run a task")
    p_run.add_argument("task_name", help="Task to run")
```

Gives `conda yourplugin <TAB>` with `list` and `run`, and
`conda yourplugin run <TAB>` with task completion.

### Choices

For flags with a fixed set of values, use `choices`:

```python
parser.add_argument(
    "--format",
    choices=["json", "table", "csv"],
    help="Output format",
)
```

These are offered as candidates on `--format <TAB>`.

conda-completion also fills selected conda-provided static choices that
are not represented as argparse choices. Today that includes conda
configuration parameter names for `conda config` and health check names
for `conda doctor` / `conda check`.

### Mutually exclusive groups

Wrap conflicting flags in a mutually exclusive group.
conda-completion hides excluded flags from the completion list:

```python
group = parser.add_mutually_exclusive_group()
group.add_argument("--json", action="store_true")
group.add_argument("--table", action="store_true")
```

After the user types `--json`, `--table` is no longer offered.

### Parser construction

Keep parser construction cheap and side-effect free. Completion
generation imports plugin entry points and asks conda to build the
argparse tree. A plugin should not do network calls, scan large
directories, mutate environments, or require optional runtime state while
configuring its parser.

If a plugin import fails, conda may not be able to build the parser that
completion generation needs.

## Dynamic completion types

conda-completion infers completion types from common flag and positional
names:

| Argument name | Inferred type | Completes from |
| --- | --- | --- |
| `--name`, `--environment` | `env_name` | Project + global environments |
| `--channel` | `channel` | Project + .condarc channels |
| `--prefix` | `directory` | Shell's native directory completion |
| positional `package`, `packages` | `package_spec` | Package names and versions |
| positional `task_name` | `task_name` | Project task names |
| positional `environment` | `environment` | Project + global environments and registered environment prefixes |

Heuristics match on the long-form flag name. If your plugin uses
`--name` for an environment argument, conda-completion infers
environment-name completion.

Use conventional destination names when they match your command's
meaning. Avoid clever aliases if a normal conda spelling exists.

For arguments that need explicit metadata, attach attributes to the
argparse action:

```python
action = parser.add_argument("tool")
action.completion_type = "global_tool"
```

For positionals that may draw from more than one source, use a compound
completion spec:

```python
action = parser.add_argument("target")
action.completion = {
    "sources": ["package_spec"],
    "rules": [
        {"when_options": ["--from-file"], "sources": ["file"]},
    ],
}
```

Completion sources can be built in (`env_name`, `environment`, `channel`,
`directory`, `file`, `path`, `task_name`, `global_tool`, `package_spec`)
or plugin-defined runtime sources.

### Runtime sources and aliases

Plugin-defined runtime sources let a plugin complete small local
directories without importing Python on TAB. The currently supported
runtime source kind is `directory_entries`:

```python
action = parser.add_argument("tool")
action.completion_type = "cached_tool"
action.completion_runtime_sources = {
    "cached_tool": {
        "kind": "directory_entries",
        "description": "cached tool",
        "group": "tool",
        "home_suffix": [".conda", "global", "tools"],
        "entry_type": "directory",
        "max_entries": 10_000,
    },
}
```

The completer reads that directory at completion time, filters regular
files or directories when requested, and never runs plugin code on TAB.

If a plugin exposes a command through another executable, add parser
aliases so the generated shell scripts register completion for those
names too:

```python
parser.completion_aliases = {"cx": ["exec"]}
```

Aliases are stored in the manifest and resolved by the Rust completer.

## Authoring checklist

Good completion metadata usually comes from good argparse metadata:

- Provide a concise `summary` for each
  {external+conda:py:class}`~conda.plugins.types.CondaSubcommand`.
- Provide helpful `help` text for every option and subcommand.
- Use `choices=` for closed sets such as modes, output formats, or
  policies.
- Use `metavar=` for values whose destination name is not user-facing.
- Use mutually exclusive groups when flags cannot be combined.
- Use conventional names such as `--environment`, `--channel`, and
  `task_name`.
- Use explicit completion metadata for wrapper commands, plugin-owned
  runtime sources, and context-sensitive positional values.
- Keep parser construction cheap and reliable.

## When completions update

The manifest regenerates automatically after `conda install`,
`conda remove`, or `conda update` when the set of registered conda
plugin entry point names changes. Completions appear on the next TAB
press.

If you install the plugin outside conda's package manager during
development, run `conda completion generate` manually.

Also regenerate manually after changing an existing plugin's argparse
metadata without changing its conda entry point name.

If package metadata is not relevant to your plugin test, use:

```bash
conda completion generate --no-repodata
```

## Testing

Verify your plugin's completions are included:

```bash
conda completion generate
conda completion status
```

The `Commands` count should reflect your plugin's subcommands. Test
interactively:

```bash
conda yourplugin <TAB>
conda yourplugin --<TAB>
```

For commands with dynamic value completion, also test the value
positions:

```text
conda yourplugin --name <TAB>
conda yourplugin package-prefix<TAB>
```
