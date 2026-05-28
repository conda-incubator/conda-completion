# Coming from conda-bash-completion

[`tartansandal/conda-bash-completion`](https://github.com/tartansandal/conda-bash-completion)
is a bash-only completion tool available on conda-forge. It parses `conda
--help` output at completion time to discover commands and flags.

## What changes

| | conda-bash-completion | conda-completion |
|---|---|---|
| Shells | bash only | bash, zsh, PowerShell, fish |
| Plugin subcommands | Not supported | Automatic |
| Completion speed | Runs `conda --help` on every TAB | Reads cached manifest, no Python |
| Contextual completions | No | env names, tasks, channels |
| Descriptions | No | Yes (zsh, fish, PowerShell) |

## Migration steps

### 1. Remove conda-bash-completion

```bash
conda remove conda-bash-completion
```

If you installed it manually, remove the sourcing line from your `~/.bashrc`:

```bash
# Remove this line:
source /path/to/conda-bash-completion/conda
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

- Plugin subcommands like `conda workspace`, `conda global`, and
  `conda task` are included in the generated manifest.
- Completion avoids running `conda --help` on every TAB press. The Rust
  binary reads a pre-built manifest instead.
- If you later switch to zsh or another shell, the same tool works.
