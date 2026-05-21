# Motivation

## The landscape before conda-completion

Conda has had no built-in shell completion since version 4.4.0, which
used argcomplete. The ecosystem fragmented across several independent
projects:

| Project | Shell | Status |
|---|---|---|
| `tartansandal/conda-bash-completion` | bash | Active, on conda-forge |
| `conda-incubator/conda-zsh-completion` | zsh | Maintained, oh-my-zsh plugin |
| `bmcfee/fish-conda` | fish | Unmaintained |
| Fish built-in `conda.fish` | fish | Based on conda 4.4.11, stale |
| oh-my-bash / Bash-it plugins | bash | Minimal, basic |
| `sigoden/argc-completions` | all | Generic, covers 1000+ commands |

Every one of these tools is unaware of conda plugin subcommands. When
you install `conda-workspaces`, `conda-global`, or `conda-spawn`, none
of these tools complete the new subcommands. Users must wait for each
tool to be manually updated, which may never happen for unmaintained
projects.

## What conda-completion solves

**One tool, all shells.** Instead of maintaining separate bash, zsh,
fish, and PowerShell completion scripts, conda-completion generates
completions from the same source for all four shells.

**Plugin-aware by default.** The manifest is generated from conda's
actual argparse tree after all plugins have loaded. Any plugin that
registers `conda_subcommands` is included automatically with no
configuration or opt-in.

**Dynamic contextual completions.** Environment names, task names,
channels, and feature names are completed from project files, not
just from static definitions.

**Speed.** Existing tools either parse `conda --help` on every TAB
press (~100 ms) or use a hand-maintained static script. conda-completion
pre-generates a manifest and uses a Rust binary to read it in under 5 ms.

## Scope

conda-completion completes the `conda` command and all its Python
plugins. It does not cover `mamba` or `micromamba`, which have their own
built-in completion systems (written in C++).
