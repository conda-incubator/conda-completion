# Scope and tradeoffs

conda-completion is designed to keep the `conda` command's completions
close to the installed command tree without making every TAB press
expensive.

That leads to a few deliberate boundaries.

## What conda-completion completes

The generated manifest covers conda's argparse command tree:

- root commands such as `install`, `remove`, `env`, and plugin commands
- nested subcommands
- long and short options
- option descriptions
- argparse choices
- mutually exclusive option groups
- positional arguments that expose useful metadata

The runtime completer adds context that should stay live:

- environment names from `~/.conda/environments.txt` and project files
- registered environment prefixes for positional environment arguments
- channel names from `.condarc`, `$CONDARC`, project files, and lockfiles
- task names from supported project files
- package names and versions from cached conda repodata
- directory fallback for prefix-style arguments

## What it does not try to complete

conda-completion does not run conda, solve environments, import Python,
or query the network on TAB.

It also does not complete:

- `mamba` or `micromamba` commands
- arbitrary shell aliases that wrap `conda` without `--command-name` or
  manifest-provided alias metadata
- PyPI package names
- package build strings
- package constraints produced by a solver
- every file argument for every command
- package names from an empty package word

For package completion, type a prefix first:

```text
conda install num<TAB>
```

Version completion starts when the current word includes `=` or `==`:

```text
conda install numpy=<TAB>
conda install numpy==<TAB>
```

## Why not call conda on every TAB

Conda startup can load Python, plugins, configuration, and solver
machinery. That is appropriate for real commands, but it is too much for
interactive completion where users may press TAB repeatedly while
editing a single line.

conda-completion splits the work:

- Python performs expensive introspection during `conda completion
  generate`.
- Rust performs the latency-sensitive matching on each TAB press.
- Project files are parsed through a stat-based cache, so edits are
  noticed without rereading unchanged files.
- Package metadata is read from generated cache files and never fetched
  on TAB.

This design keeps completion responsive even when the installed conda
command tree includes several plugins.

## Why conda init still matters

`conda init` teaches your shell how to activate environments and makes
the `conda` shell function available. conda-completion registers a
completion function for the `conda` command.

Those are separate concerns. In a typical shell startup file, the conda
initialization block should run before the conda-completion hook.

See conda's {external+conda:doc}`conda init command reference
<commands/init>` for the shell initialization model.

## How plugin support works

Conda plugins add subcommands through conda's plugin API. During
generation, conda-completion asks conda for the argparse parser and walks
the resulting tree. A plugin that provides good argparse metadata gets
completion support without a conda-completion-specific integration.

See conda's {external+conda:doc}`subcommand plugin documentation
<dev-guide/plugins/subcommands>`.

## How channel configuration shapes package completion

Package names and versions are collected from conda repodata for the
channels and subdirs in the current conda context. This follows conda's
normal configuration system, including `.condarc`, environment
variables, proxy configuration, custom channels, and private channel
credentials.

Conda documents {external+conda:doc}`.condarc
<user-guide/configuration/use-condarc>` and {external+conda:doc}`channel
configuration <user-guide/configuration/settings>` in its user guide.

The generated completion cache should be considered local to the channel
configuration and credentials that produced it.
