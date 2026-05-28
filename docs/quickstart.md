# Quick start

Get conda tab completion working in under a minute.

## Prerequisites

- conda 25.1 or later
- A supported shell: bash, zsh, PowerShell, or fish
- `conda` available in new shell sessions

If `conda` is not available in a fresh terminal, run
{external+conda:doc}`conda init <commands/init>` for your shell first,
restart the terminal, and continue.

## Install

:::::{tab-set}

::::{tab-item} conda (recommended)

```bash
conda install -c conda-forge conda-completion
```

::::

::::{tab-item} pixi

```bash
pixi global install conda-completion
```

::::

:::::

## Activate completion

```bash
conda completion install
```

This auto-detects your shell, generates the completion manifest, and
adds a hook to your shell's RC file. Preview what it will do with
`--dry-run`:

```bash
conda completion install --dry-run
```

:::{tip}
To target a specific shell, pass it explicitly:
`conda completion install zsh`
:::

If you are building a container, working offline, or only need command
and flag completion, skip package metadata during setup:

```bash
conda completion install --yes --no-repodata
```

## Try it out

Open a new shell (or source your RC file) and press TAB:

:::{image} ../demos/quickstart.gif
:alt: conda-completion quickstart demo
:width: 100%
:::

```text
$ conda ins<TAB>
install   -- Install a list of packages into a specified conda environment

$ conda install --<TAB>
--channel     -- Additional channel to search for packages
--dry-run     -- Only display what would have been done
--name        -- Name of environment
...
```

If a plugin such as `conda-workspaces` is installed, plugin subcommands
come from the same generated manifest:

```text
$ conda workspace <TAB>
activate  add  archive  clean  envs  export  import  info  init  install ...
```

Check the generated files and runtime binary:

```bash
conda completion status
```

## What's next?

- {doc}`tutorials/index` for per-shell walkthroughs, project-aware completion, and migration guides
- {doc}`how-to/diagnose-and-repair` when completion does not behave as expected
- {doc}`reference/index` for the CLI command reference and manifest format
- {doc}`explanation/scope-and-tradeoffs` for what is completed and what is intentionally out of scope
