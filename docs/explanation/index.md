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

:::{grid-item-card} {octicon}`filter` Scope and tradeoffs
:link: scope-and-tradeoffs
:link-type: doc

What conda-completion completes, what it avoids, and why those lines exist.
:::

:::{grid-item-card} {octicon}`zap` Performance
:link: performance
:link-type: doc

Why Rust is on the hot path and how the stat-based cache keeps latency low.
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
