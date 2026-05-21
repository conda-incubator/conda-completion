# Completing plugin subcommands

One of conda-completion's key strengths is automatic support for plugin
subcommands. This tutorial shows how it works.

## How plugins are discovered

When the completion manifest is generated (during `conda completion
install` or explicitly via `conda completion generate`),
conda-completion calls `conda.cli.conda_argparse.generate_parser()`,
which loads all registered plugins and adds their subcommands to the
argparse tree. The introspection code then walks the entire tree,
including plugin subcommands.

This means every plugin that registers via `conda_subcommands` is
automatically included with no extra configuration.

## Example: conda-workspaces

After installing `conda-workspaces`:

```bash
conda install -c conda-forge conda-workspaces
```

The completion manifest is regenerated automatically (via the post-command
hook). You can immediately complete workspace subcommands:

:::{image} ../../demos/subcommand-completion.gif
:alt: Subcommand completion demo
:width: 100%
:::

```text
$ conda workspace <TAB>
activate  add  archive  clean  envs  export  import  info  init
install   list  lock  quickstart  remove  run  shell  unarchive

$ conda workspace install --<TAB>
--environment  -- Target environment
--force        -- Force install
--dry-run      -- Only display what would have been done

$ conda task <TAB>
add  export  list  remove  run
```

## Example: conda-global

```text
$ conda global <TAB>
add  edit  ensurepath  expose  hide  install  list  migrate
pin  remove  run  sync  tree  uninstall  unpin  update

$ conda global install --<TAB>
--channel  -- Additional channel to search
--force    -- Force reinstall
```

## Contextual completions from project files

When you are in a directory with a `conda.toml`, environment names
and task names from that file are completed dynamically:

:::{image} ../../demos/dynamic-completion.gif
:alt: Dynamic completion from project files
:width: 100%
:::

```text
$ cat conda.toml
[environments]
dev = {}
ci = {}

[tasks]
test = "pytest"
lint = "ruff check"

$ conda workspace install -e <TAB>
dev  ci

$ conda task run <TAB>
test  lint
```

## What happens when you install or remove a plugin

The `conda_post_commands` hook runs after `conda install`, `conda remove`,
and `conda update`. It hashes the set of registered plugin entry point
names and compares against the hash stored in the manifest. If they
differ, the manifest is regenerated automatically.

This covers:
- `conda install conda-workspaces`
- `conda remove conda-workspaces`
- `conda self install conda-global` (if conda-self is installed)

For plugins installed via pip, run `conda completion generate` manually.
