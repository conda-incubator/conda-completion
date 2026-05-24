---
orphan: true
---

# Explanation

Understanding the design decisions behind conda-completion.

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} {octicon}`light-bulb` Motivation
:link: motivation
:link-type: doc

Why conda-completion exists and the landscape it replaces.
:::

:::{grid-item-card} {octicon}`cpu` Architecture
:link: architecture
:link-type: doc

How the hybrid Python/Rust design works and why it was chosen.
:::

:::{grid-item-card} {octicon}`zap` Performance
:link: performance
:link-type: doc

Why Rust, benchmarks, and the stat-based caching strategy.
:::

:::{grid-item-card} {octicon}`database` Caching
:link: caching
:link-type: doc

Stat-based file cache, manifest lifecycle, and version lookups.
:::

:::{grid-item-card} {octicon}`shield` Security
:link: security
:link-type: doc

Trust boundaries, output sanitization, symlink protection, and atomic writes.
:::

:::{grid-item-card} {octicon}`question` FAQ
:link: faq
:link-type: doc

Common questions and answers.
:::

::::
