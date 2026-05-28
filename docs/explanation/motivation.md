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

These tools do not generally discover conda plugin subcommands. When a
user installs `conda-workspaces`, `conda-global`, or `conda-spawn`, the
completion script needs plugin-specific updates unless it can read
conda's command tree directly.

## What conda-completion solves

**One tool, all shells.** Instead of maintaining separate bash, zsh,
fish, and PowerShell completion scripts, conda-completion generates
completions from the same source for all four shells.

**Plugin-aware by default.** The manifest is generated from conda's
argparse tree after plugins have loaded. Plugins that register
{external+conda:doc}`conda_subcommands <dev-guide/plugins/subcommands>`
are included when the manifest is generated, with no
conda-completion-specific configuration.

**Dynamic contextual completions.** Environment names, task names, and
channels are completed from project files, not just from static
definitions.

**Speed.** Existing tools either parse `conda --help` on every TAB
press (slow due to Python startup) or use a hand-maintained static
script. conda-completion pre-generates a manifest and uses a Rust binary
to read it directly, with no Python process on the hot path.

## Scope

conda-completion completes the `conda` command and registered
subcommands from Python plugins. It does not cover `mamba` or
`micromamba`, which have their own built-in completion systems.
