# Migrating from existing tools

conda-completion replaces several shell-specific, independently maintained
completion projects. These guides walk through removing your current tool
and switching to conda-completion.

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} conda-bash-completion
:link: conda-bash-completion
:link-type: doc

The most common existing solution for bash users.
:::

:::{grid-item-card} conda-zsh-completion
:link: conda-zsh-completion
:link-type: doc

A hand-written zsh completion script with a 12-hour package cache.
:::

:::{grid-item-card} fish-conda
:link: fish-conda
:link-type: doc

Fish plugin or the built-in `conda.fish` completions.
:::

:::{grid-item-card} Other tools
:link: other-tools
:link-type: doc

argc-completions, oh-my-bash, Bash-it, and other framework plugins.
:::

::::

```{toctree}
:hidden:

conda-bash-completion
conda-zsh-completion
fish-conda
other-tools
```
