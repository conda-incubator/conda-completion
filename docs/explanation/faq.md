# FAQ

## Does this work with mamba or micromamba?

No. mamba 2.x is a standalone C++ application with its own built-in
`shell completion` command. conda-completion covers the `conda` command
and all its Python plugins. If you use both `conda` and `mamba`, you
can have both completion systems installed side by side without
conflict.

## Do I need to regenerate after installing a plugin?

Usually not. conda-completion registers a post-command hook that
checks whether the set of installed plugins has changed after
`conda install`, `conda remove`, and `conda update`. If a plugin was
added or removed, the manifest is regenerated automatically.

The one exception is plugins installed directly via pip (outside of
conda's package manager). In that case, run:

```bash
conda completion generate
```

## Which shells are supported?

bash, zsh, PowerShell, and fish. bash, zsh, and PowerShell are
Tier 1 (fully tested in CI). fish is Tier 2 (community-tested,
best-effort). See {doc}`../reference/shell-support` for the full
feature matrix.

## Why does bash not show descriptions?

bash's built-in completion system (`complete`/`compgen`) does not
support displaying descriptions alongside candidates. zsh, fish, and
PowerShell all support this natively.

If you want descriptions in bash, consider switching to zsh (which is
the default shell on macOS) or using a bash completion framework that
supports descriptions.

## How fast is it?

Effectively instant for commands, flags, and package names. No Python
process starts on TAB press. Version completion and fuzzy matching do
more work but still feel responsive. See {doc}`performance` for details.

## Where is the manifest stored?

In your platform's cache directory:

| Platform | Path |
|---|---|
| Linux | `~/.cache/conda/completion/completion.msgpack` |
| macOS | `~/Library/Caches/conda/completion/completion.msgpack` |
| Windows | `%LOCALAPPDATA%\conda\cache\completion\completion.msgpack` |

The manifest is regenerated data (not user configuration), so it
belongs in the cache directory. Deleting it is safe; run
`conda completion generate` to recreate it.

## Can I use this alongside other completion tools?

You should remove any existing conda completion tools before installing
conda-completion to avoid conflicts. See the
{doc}`migration guides <../tutorials/coming-from/index>` for
step-by-step instructions for each tool.

## Does it complete package names?

Yes. During `conda completion generate`, package names are extracted
from repodata for all configured channels unless you pass
`--no-repodata`. After that, `conda install nump<TAB>` completes
matching package names.

Package names are stored in `completion.msgpack` alongside the command
tree, so they are always available without extra file reads.

Package metadata is reused for 24 hours. Use
`conda completion refresh` to force a refresh.

## Does it complete package versions?

Yes. When you type `=` or `==` after a package name, the completer
loads version data from `versions.index` and `versions.store`:

```text
$ conda install numpy=<TAB>
numpy=1.26.4  numpy=2.0.0  numpy=2.1.0  ...
```

The version files are only loaded when `=` is detected, keeping the
common TAB press fast.

## What if I misspell a package name?

The completer uses a three-tier matching strategy: prefix match first,
then substring match, then fuzzy similarity via normalized
Damerau-Levenshtein distance. Typos like `numpie`, `nupmy`, or
`scikitlearn` (missing hyphen) will suggest the correct package.

The similarity threshold is 0.6 with a cap of 10 results, so you will
not be flooded with irrelevant suggestions.

## Does it complete environment names from my project?

Yes. The Rust binary walks upward from your working directory looking
for `conda.toml`, `pixi.toml`, or `pyproject.toml` (with
`[tool.conda]` or `[tool.pixi]` sections). Environment names, task
names, feature names, and channels defined in these files are available
as completion candidates.

It also reads `~/.conda/environments.txt` for all registered
environments and `~/.condarc` for configured channels.

## What happens if the manifest is stale?

If you install a new plugin and the automatic regeneration hook does
not fire (for example, the plugin was installed via pip), completions
for that plugin's subcommands will be missing. Running
`conda completion generate` fixes this immediately.

Contextual completions (environment names, task names, channels) are
always fresh because they are read directly from project and global
files on every TAB press, not from the manifest.

## What about cmd.exe on Windows?

cmd.exe does not have a programmable completion API. There is no way to
register a custom completer for a command in cmd.exe; its built-in TAB
key only cycles through file and directory names. This is a limitation
of cmd.exe itself, not of conda-completion.

Windows users who want tab completion should use PowerShell, which is
installed by default on all modern Windows versions and has full
completion support.

## Can conda packages ship their own completions?

conda-completion and per-package completion scripts solve different
problems. conda-completion covers the `conda` CLI and its plugin
subcommands. A separate, orthogonal need in the conda ecosystem is for
conda packages to register shell completions for their own commands
(e.g., a package that installs a `mytool` binary wanting to provide
`mytool <TAB>`).

That is outside conda-completion's scope. It would require a
convention for packages to declare completion scripts (e.g., a hook
directory or metadata field) and for conda's activation system to
source them. If such a convention is adopted in the future,
conda-completion could potentially integrate with it, but the two
concerns are independent.

## How do I uninstall?

```bash
conda completion uninstall
conda remove conda-completion
```

The first command removes the completion hook from your shell's RC
file. The second removes the package. The cached manifest and context
cache are left behind in the cache directory; delete them manually if
you want a clean removal.
