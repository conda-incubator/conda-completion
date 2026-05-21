# Coming from other tools

## argc-completions

[`sigoden/argc-completions`](https://github.com/sigoden/argc-completions)
provides completions for 1000+ commands including conda. It supports bash,
zsh, fish, PowerShell, Nushell, and Elvish.

argc-completions uses a generic approach that works across many tools but
cannot provide conda-specific features like plugin subcommand discovery or
contextual completions from project files.

**To migrate:**

1. Remove the conda entry from your argc-completions config.
2. Install conda-completion: `conda install -c conda-forge conda-completion`
3. Activate: `conda completion install <your-shell>`

## oh-my-bash / Bash-it

Some bash frameworks include basic conda completion plugins. These are
typically minimal and unaware of plugin subcommands.

**To migrate:**

1. Remove the conda completion plugin from your framework config.
2. Install conda-completion: `conda install -c conda-forge conda-completion`
3. Activate: `conda completion install bash`

## zsh frameworks (oh-my-zsh, prezto, zinit)

If your zsh framework provides conda completions (often via the
`conda-zsh-completion` project), see the dedicated
{doc}`conda-zsh-completion` migration guide.

## mamba / micromamba

mamba 2.x has its own built-in `shell completion` command for generating
completions. conda-completion does not cover mamba commands; it only
completes `conda` and its Python plugins. If you use both `conda` and
`mamba`, you can run both completion systems side by side.
