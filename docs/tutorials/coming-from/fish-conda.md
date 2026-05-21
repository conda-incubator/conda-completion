# Coming from fish-conda or built-in completions

Fish provides conda completions from two sources:

- [`bmcfee/fish-conda`](https://github.com/bmcfee/fish-conda): a
  community fish plugin (unmaintained)
- Fish's built-in `conda.fish`: ships with fish, based on conda 4.4.11

Both are stale and unaware of modern conda features and plugins.

## Migration steps

### 1. Remove existing completions

If you use `fish-conda` via fisher:

```fish
fisher remove bmcfee/fish-conda
```

If you use fish's built-in completions and want to prevent conflicts:

```fish
rm (status fish-path)/share/fish/vendor_completions.d/conda.fish
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

Open a new fish session. Completions should work immediately, including
tab-separated descriptions for each candidate.

## What you gain

- Completions that match your actual conda installation instead of a
  frozen snapshot from conda 4.4.
- Plugin subcommands (workspace, global, spawn, task) are completed
  automatically.
- Contextual completions from project files.
