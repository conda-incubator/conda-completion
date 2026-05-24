# Plugin completions

How conda-completion discovers your plugin's subcommands, and how to
make your plugin work well with it.

## Discovery

conda-completion calls conda's `generate_parser()` to walk the full
argparse tree, including all plugin-registered subcommands. If your
plugin uses the `conda_subcommands` hook with a `configure_parser`
callback, your flags, positionals, and subcommands are included in the
manifest automatically. No extra configuration needed.

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

`metavar` tells users what kind of value a flag expects and helps
conda-completion infer the dynamic completion type:

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
    p_run.add_argument("task", help="Task to run")
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

### Mutually exclusive groups

Wrap conflicting flags in a mutually exclusive group.
conda-completion hides excluded flags from the completion list:

```python
group = parser.add_mutually_exclusive_group()
group.add_argument("--json", action="store_true")
group.add_argument("--table", action="store_true")
```

After the user types `--json`, `--table` is no longer offered.

## Dynamic completion types

conda-completion infers completion types from flag names:

| Flag name | Inferred type | Completes from |
| --- | --- | --- |
| `--name`, `--environment` | `env_name` | Project + global environments |
| `--channel` | `channel` | Project + .condarc channels |
| `--prefix` | `directory` | Shell's native directory completion |

Heuristics match on the long-form flag name. If your plugin uses
`--name` for an environment argument, it gets environment name
completion automatically.

## When completions update

The manifest regenerates automatically after `conda install`,
`conda remove`, or `conda update` when the plugin set changes.
Completions appear on the next TAB press.

If you install via `pip install` directly (during development), run
`conda completion generate` manually.

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
