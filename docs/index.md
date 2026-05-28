# conda-completion

Fast, plugin-aware shell tab completion for conda.

conda-completion introspects conda's argparse command tree, including
registered plugin subcommands such as workspace, global, spawn, and task
when those plugins are installed. A small Rust binary handles each TAB
press with no Python on the hot path, and shells with native description
support can show help text alongside candidates.

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

Understanding shell detection, cache files, and package metadata.
:::

:::{grid-item-card} {octicon}`tools` Troubleshooting
:link: how-to/troubleshooting
:link-type: doc

Common issues and how to fix them.
:::

:::{grid-item-card} {octicon}`zap` Features
:link: features
:link-type: doc

Feature overview and shell behavior.
:::

::::::

## Highlights

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item}

**Plugin-aware completions**

Conda plugins that register subcommands are included when the manifest
is generated. Install a plugin such as `conda-workspaces`, regenerate if
needed, and `conda workspace <TAB>` offers its subcommands and flags.

:::

:::{grid-item}

**Contextual completions**

Environment names, task names, and channels are completed from your
project and environment files: `environment.yml`, conda-workspaces
manifests such as `conda.toml`, pixi manifests, `pyproject.toml`, and
lockfiles.

:::

:::{grid-item}

**Package name and version completion**

`conda install nump<TAB>` completes package names from repodata.
`conda install numpy=<TAB>` lists available versions. A three-stage
matching strategy handles typos: prefix, substring, then fuzzy
Damerau-Levenshtein similarity.

:::

:::{grid-item}

**Descriptions alongside candidates**

In zsh, fish, and PowerShell, each completion candidate can show the
help text extracted from conda's argparse metadata.

:::

:::{grid-item}

**Instant response**

A tiny Rust binary handles every TAB press. A stat-based file cache
avoids re-parsing files that have not changed. No Python runs on the
hot path.

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
Project-aware completions <tutorials/project-aware-completions>
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
Environment variables <reference/environment-variables>
Errors <reference/errors>
```

```{toctree}
:hidden:
:caption: Explanation

Motivation <explanation/motivation>
Architecture <explanation/architecture>
Scope and tradeoffs <explanation/scope-and-tradeoffs>
Performance <explanation/performance>
Caching <explanation/caching>
Security <explanation/security>
FAQ <explanation/faq>
features
configuration
```

```{toctree}
:hidden:
:caption: How-to guides

Troubleshooting <how-to/troubleshooting>
Diagnose and repair <how-to/diagnose-and-repair>
Nonstandard shell startup <how-to/nonstandard-shell-startup>
Remote & automated environments <how-to/remote-and-automated-environments>
Offline & restricted networks <how-to/offline-and-restricted-networks>
Package metadata <how-to/package-metadata>
Plugin completions <how-to/custom-completions>
```

```{toctree}
:hidden:
:caption: Project

changelog
```
