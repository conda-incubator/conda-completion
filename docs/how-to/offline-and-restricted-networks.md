# Use completion offline or on restricted networks

conda-completion can work without network access. The main decision is
whether you need package name and version candidates, or only command,
flag, plugin, project, environment, task, and channel candidates.

## Choose a metadata mode

Use full metadata when users expect package completion:

```bash
conda completion generate
```

Use command-only generation when network access is unavailable, slow, or
unwanted:

```bash
conda completion generate --no-repodata
```

The command-only mode still includes:

- conda commands and options
- installed plugin subcommands
- argparse choices
- mutually exclusive option behavior
- project environment names
- project task names
- configured channels
- registered conda environments

It omits package names and package versions.

## Pre-generate while online

For air-gapped development machines, generate once while online:

```bash
conda completion generate
conda completion status
```

Copy the cache directory printed by status to the same platform and user
location on the offline machine. The cache contains:

- `completion.msgpack`
- `versions.index`
- `versions.store`
- `context_cache.msgpack` if project files have been completed before

Regenerate with `--no-repodata` later if command metadata changes while
offline and package metadata cannot be refreshed.

## Build container images

For an interactive container where package completion is useful:

```dockerfile
RUN conda install -y -c conda-forge conda-completion && \
    conda completion install bash --yes
```

For a lean image or CI image where package completion is unnecessary:

```dockerfile
RUN conda install -y -c conda-forge conda-completion && \
    conda completion install bash --yes --no-repodata
```

Generate as the same user that will use the shell. A manifest generated
as `root` lives in root's cache directory, not a later non-root user's
cache directory.

## Respect conda network configuration

Package metadata extraction uses conda's repodata machinery. That means
the same channel, proxy, certificate, credential, and offline settings
that affect `conda install` also affect `conda completion generate`.

Useful checks:

```bash
conda config --show channels
conda config --show proxy_servers
conda info
```

If your organization uses a private mirror, configure conda first. Then
refresh completion metadata:

```bash
conda completion refresh
```

See conda's {external+conda:doc}`configuration settings
<user-guide/configuration/settings>` and {external+conda:doc}`.condarc
guide <user-guide/configuration/use-condarc>` for the settings that feed
this context.

## Keep private channels private

The manifest stores package names and version strings, not package
tarballs. It can still reveal private package names. Treat generated
completion caches as developer-local data when private channels are in
use.

Avoid copying caches between users or machines with different channel
permissions unless that is acceptable for your organization.

## Recover from failed repodata reads

When package metadata refresh fails, conda-completion preserves existing
package metadata if valid files are already present. If no package
metadata exists, it still writes command and flag completion data.

To intentionally stay offline:

```bash
conda completion generate --no-repodata
```

To retry package metadata later:

```bash
conda completion refresh
```
