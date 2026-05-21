# Quick start

Get conda tab completion working in under a minute.

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

$ conda workspace <TAB>
activate  add  archive  clean  envs  export  import  info  init  install ...
```

## What's next?

- {doc}`tutorials/index` for per-shell walkthroughs and migration guides
- {doc}`reference/index` for the CLI command reference and manifest format
- {doc}`explanation/architecture` for how the hybrid Python/Rust design works
