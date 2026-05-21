# Setting up fish completion

This guide walks through setting up conda tab completion in fish.

:::{note}
Fish is a Tier 2 shell. It is community-tested and maintained on a
best-effort basis. Please report issues on the
[issue tracker](https://github.com/conda-incubator/conda-completion/issues).
:::

## Prerequisites

- conda 25.1 or later
- fish 3.0 or later

## Install conda-completion

```bash
conda install -c conda-forge conda-completion
```

## Activate completion

### Option A: automatic install

```bash
conda completion install
```

This detects fish from your `$SHELL` variable and adds a delimited block
to `~/.config/fish/config.fish`. Preview with:

```bash
conda completion install --dry-run
```

### Option B: manual setup

Add this line to `~/.config/fish/config.fish`:

```fish
conda completion init fish | source
```

## Verify

Open a new fish session and try:

```text
$ conda install --<TAB>
--channel  (Additional channel to search for packages)
--dry-run  (Only display what would have been done)
--name     (Name of environment)
```

Fish natively supports tab-separated descriptions, so help text appears
alongside each candidate.

## Replacing fish's built-in conda completions

Fish ships a built-in `conda.fish` completions file based on conda 4.4.
conda-completion replaces it entirely. If you see duplicate or stale
completions, remove the built-in file:

```fish
rm (status fish-path)/share/fish/vendor_completions.d/conda.fish
```

Or, if you installed fish via Homebrew:

```fish
rm (brew --prefix)/share/fish/vendor_completions.d/conda.fish
```

## Uninstall

```bash
conda completion uninstall
```
