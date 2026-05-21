# conda-completion

Fast, plugin-aware shell tab completion for conda.

conda-completion introspects conda's full command tree, including all installed
plugin subcommands (workspace, global, spawn, task, and more), and provides
instant TAB completions with descriptions. A small Rust binary handles every
TAB press in under 5 ms with no Python on the hot path.

```bash
conda install -c conda-forge conda-completion
conda completion install
```

:::{image} ../demos/quickstart.gif
:alt: conda-completion quickstart demo
:width: 100%
:::

---

::::::{grid} 1 1 2 3
:gutter: 3

:::{grid-item-card} {octicon}`rocket` Quick start
:link: quickstart
:link-type: doc

Install and activate shell completion in under a minute.
:::

:::{grid-item-card} {octicon}`mortar-board` Tutorials
:link: tutorials/index
:link-type: doc

Per-shell setup guides and migration from existing completion tools.
:::

:::{grid-item-card} {octicon}`book` Reference
:link: reference/index
:link-type: doc

CLI commands, manifest format, shell support matrix, and binary interface.
:::

:::{grid-item-card} {octicon}`light-bulb` Explanation
:link: explanation/index
:link-type: doc

Why conda-completion exists, how the hybrid architecture works, and performance details.
:::

:::{grid-item-card} {octicon}`gear` Configuration
:link: configuration
:link-type: doc

Customizing shell detection, manifest paths, and cache behavior.
:::

:::{grid-item-card} {octicon}`zap` Features
:link: features
:link-type: doc

Everything conda-completion brings to the table.
:::

::::::

## Highlights

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item}

**Plugin-aware completions**

Every conda plugin that registers subcommands is automatically included.
Install `conda-workspaces` and `conda workspace <TAB>` just works, with
full subcommand and flag completion.

:::

:::{grid-item}

**Contextual completions**

Environment names, task names, and channels are completed from your
project files: `conda.toml`, `pixi.toml`, `pyproject.toml`,
`environment.yml`, and lockfiles.

:::

:::{grid-item}

**Descriptions alongside candidates**

In zsh, fish, and PowerShell, each completion candidate shows its help
text so you never have to guess what a flag does.

:::

:::{grid-item}

**Sub-5 ms response time**

A tiny Rust binary (under 1 MB) handles every TAB press. A stat-based
file cache avoids re-parsing files that have not changed. No Python
runs on the hot path.

:::

::::

```{toctree}
:hidden:

quickstart
```

```{toctree}
:hidden:
:caption: Tutorials

Bash <tutorials/setup-bash>
Zsh <tutorials/setup-zsh>
PowerShell <tutorials/setup-powershell>
Fish <tutorials/setup-fish>
Plugin completions <tutorials/plugin-completions>
Migrating <tutorials/coming-from/index>
```

```{toctree}
:hidden:
:caption: Reference

CLI <reference/cli>
Manifest format <reference/manifest>
Completer binary <reference/completer-binary>
Shell support <reference/shell-support>
```

```{toctree}
:hidden:
:caption: Explanation

Motivation <explanation/motivation>
Architecture <explanation/architecture>
Performance <explanation/performance>
FAQ <explanation/faq>
features
configuration
```

```{toctree}
:hidden:
:caption: Project

changelog
```
