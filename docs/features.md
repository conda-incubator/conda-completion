# Features

## Plugin-aware completion

conda-completion introspects conda's full argparse tree after all plugins
have loaded. Every plugin that registers subcommands via `conda_subcommands`
is automatically included. No configuration, no opt-in required.

Installed plugin commands are completed with the same fidelity as built-in
commands: subcommands, flags, flag values, and help descriptions.

## Contextual completions

The completer reads your project files to provide context-aware candidates:

| What's completed | Source files |
|---|---|
| Environment names | `conda.toml`, `pixi.toml`, `pyproject.toml`, `environment.yml`, `conda.lock`, `pixi.lock`, `anaconda-project.yml`, `conda-project.yml`, `~/.conda/environments.txt` |
| Task names | `conda.toml`, `pixi.toml`, `pyproject.toml`, `anaconda-project.yml`, `conda-project.yml` |
| Feature names | `conda.toml`, `pixi.toml`, `pyproject.toml` |
| Channel names | `conda.toml`, `pixi.toml`, `pyproject.toml`, `conda-lock.yml`, `conda.lock`, `pixi.lock`, `.condarc` |
| Global tool names | `~/.conda/global/global.toml` |

## Descriptions alongside candidates

In shells that support it (zsh, fish, PowerShell), each candidate is shown
with its help text:

:::{image} ../demos/option-completion.gif
:alt: Option completion with descriptions
:width: 100%
:::

```text
$ conda install --<TAB>
--channel     -- Additional channel to search for packages
--dry-run     -- Only display what would have been done
--name        -- Name of environment
--prefix      -- Full path to environment location
```

## Package name completion

`conda install nump<TAB>` completes package names extracted from
configured channels during `conda completion generate`. Over 30,000
package names are searched in under 1 ms.

## Version completion

When `=` or `==` is detected in the current word, the completer loads
version data and lists available versions:

```text
$ conda install numpy=<TAB>
numpy=1.26.4  numpy=2.0.0  numpy=2.1.0  ...
```

Version data is stored in a separate `versions.msgpack` file that is
only loaded when needed, keeping the common TAB press fast.

## Fuzzy matching

Misspelled a package name? The completer falls back to fuzzy matching
using normalized Damerau-Levenshtein similarity. Typos like `numpie`,
`nupmy`, or `scikitlearn` still find the right package.

The matching uses a three-tier strategy:

1. **Prefix match** -- the common case, essentially free
2. **Substring match** -- catches partial input anywhere in the name
3. **Similarity match** -- handles typos (transpositions, insertions,
   deletions, substitutions) with a 0.6 threshold, capped at 10 results

## Sub-5 ms response time

A Rust binary handles every TAB press. No Python process starts on the
hot path. A stat-based file cache avoids re-parsing files that have not
changed since the last TAB press.

| Scenario | Typical time |
|---|---|
| Cache hit (common case) | < 5 ms |
| Package name completion | < 7 ms |
| Version completion | < 15 ms |
| Cache miss (file changed) | < 20 ms |

## Automatic manifest regeneration

After `conda install`, `conda remove`, or `conda update`, a post-command
hook checks whether the set of registered plugins has changed. If it has,
the completion manifest is regenerated automatically. You never need to
run `conda completion generate` manually after installing a plugin via
conda.

## Tiered shell support

| Shell | Tier | Notes |
|---|---|---|
| bash | Tier 1 | Fully tested in CI on every push |
| zsh | Tier 1 | Fully tested in CI on every push |
| PowerShell | Tier 1 | Fully tested in CI on every push |
| fish | Tier 2 | Community-tested, best-effort |

## Install and uninstall commands

`conda completion install` and `conda completion uninstall` manage a
delimited block in your shell's RC file. The install command is
idempotent (running it twice does not duplicate the block) and supports
`--dry-run` to preview changes without writing.
