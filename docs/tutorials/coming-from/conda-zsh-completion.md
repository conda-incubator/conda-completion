# Coming from conda-zsh-completion

[`conda-incubator/conda-zsh-completion`](https://github.com/conda-incubator/conda-zsh-completion)
is a hand-written zsh completion script (~30 KB) that provides extensive
completions for conda's built-in commands.

## What changes

| | conda-zsh-completion | conda-completion |
|---|---|---|
| Shells | zsh only | bash, zsh, PowerShell, fish |
| Plugin subcommands | Not supported | Automatic |
| Maintenance model | Hand-maintained | Generated from argparse tree |
| Package cache | 12-hour local cache | Stat-based, instant invalidation |

## Migration steps

### 1. Remove conda-zsh-completion

If you installed it as an oh-my-zsh plugin:

```bash
# Remove from plugins list in ~/.zshrc:
# plugins=(... conda-zsh-completion ...)
rm -rf ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/conda-zsh-completion
```

If you added it to `$fpath` manually, remove those lines from `~/.zshrc`.

If you installed it from conda-forge:

```bash
conda remove conda-zsh-completion
```

### 2. Install conda-completion

```bash
conda install -c conda-forge conda-completion
```

### 3. Activate

```bash
conda completion install
```

### 4. Restart your shell

Open a new terminal and test `conda <TAB>`.

## What you gain

- Plugin subcommands come from the generated manifest instead of waiting
  for the completion script to be manually updated.
- The completion data is generated from your installed conda argparse
  tree instead of a hand-written snapshot.
- Contextual completions for environment names, task names, and
  channels from project files.
