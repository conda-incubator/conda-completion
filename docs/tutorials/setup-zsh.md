# Setting up zsh completion

This guide walks through setting up conda tab completion in zsh.

## Prerequisites

- conda 25.1 or later
- zsh 5.0 or later

## Install conda-completion

```bash
conda install -c conda-forge conda-completion
```

## Activate completion

### Option A: automatic install

```bash
conda completion install
```

This detects zsh from your `$SHELL` variable and adds a delimited block
to your `~/.zshrc`. Preview with:

```bash
conda completion install --dry-run
```

### Option B: manual setup

Add this line to your `~/.zshrc`:

```zsh
eval "$(conda completion init zsh)"
```

## Verify

Open a new terminal and try:

```text
$ conda install --<TAB>
--channel     -- Additional channel to search for packages
--dry-run     -- Only display what would have been done
--name        -- Name of environment
```

:::{tip}
In zsh, descriptions appear alongside each candidate. This is one of
the advantages over bash completion.
:::

## How it works in zsh

The generated script is a `#compdef conda` completion function. On each
TAB press, zsh calls `_conda()` which invokes the Rust binary. Output
uses `candidate:description` format, which zsh's `_describe` function
renders with aligned descriptions.

## Uninstall

```bash
conda completion uninstall
```
