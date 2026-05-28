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

## Example

:::{image} ../demos/quickstart.gif
:alt: conda-completion completing conda commands and options
:width: 720px
:::

## Start here

- {doc}`quickstart` for installation and a first completion check.
- {doc}`tutorials/index` for shell-specific setup, project-aware
  completions, plugin completions, and migration guides.
- {doc}`how-to/index` for troubleshooting, nonstandard shell startup,
  remote environments, offline setup, package metadata, and plugin
  authoring.
- {doc}`reference/index` for command syntax, shell support, environment
  variables, the manifest format, and the Rust completer interface.
- {doc}`explanation/index` for architecture, caching, performance,
  scope, security, and design tradeoffs.

## What it covers

- bash, zsh, PowerShell, and fish shell integration.
- Registered conda plugin subcommands when the manifest is generated.
- Environment names, task names, channels, package names, and package
  versions from conda and project metadata.
- Candidate descriptions in shells that support them.
- A Rust completion path that avoids starting Python on each TAB press.

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
