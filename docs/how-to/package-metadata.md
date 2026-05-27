# Manage package metadata

Package names and versions come from conda repodata. conda-completion
collects that metadata during `conda completion generate` and reuses it
for 24 hours to keep normal regeneration fast.

## Refresh repodata now

Run this when a newly published package or version is missing from
completion results:

```bash
conda completion refresh
```

This refreshes package names in `completion.msgpack` and package versions
in `versions.index` and `versions.store`.

## Skip package data

Run this in CI, containers, or offline environments when you only need
command, flag, plugin, environment, task, and channel completion:

```bash
conda completion generate --no-repodata
```

The same control is available during shell-hook installation:

```bash
conda completion install --yes --no-repodata
```

## Check what exists

Use `status` to see whether package metadata files are present:

:::{image} ../../demos/repodata-controls.gif
:alt: Package metadata controls demo
:width: 100%
:::

```bash
conda completion status
```

Look for `Package versions index` and `Package versions store`. If either
file is missing, version completion such as `conda install numpy=<TAB>`
will not have package-version candidates.

## Recover from repodata failures

If package metadata refresh fails and existing package data is present,
conda-completion preserves the existing package names and versions. If no
package data exists, it still writes command and flag completion data.

For offline setup with package completion, generate once while online,
then cache the platform cache directory shown by `conda completion status`.
