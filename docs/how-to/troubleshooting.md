# Troubleshooting

## Completions stopped working

Regenerate the manifest:

```bash
conda completion generate
```

If that doesn't help, check that the shell hook is installed:

```bash
conda completion status
```

## "Completion data not found"

The manifest does not exist. First install or cleared cache.

```bash
conda completion generate
conda completion install
```

## "Completion engine binary not found"

The `conda-completer` package is missing.

```bash
conda install conda-completer
```

If installed but the error persists, check `conda completion status`
for the binary path.

## "Cannot read completion data"

Corrupt manifest. Delete and regenerate:

```bash
rm "$(conda completion status 2>&1 | grep Manifest: | awk '{print $2}')"
conda completion generate
```

## "Shell 'X' is not supported"

Unsupported shell name passed to `install` or `init`. Supported:

- Tier 1 (CI-tested): `bash`, `zsh`, `powershell`
- Tier 2 (community-tested): `fish`

## Completions are slow

If tab completion takes more than 200 ms:

1. Regenerate the manifest:

   ```bash
   conda completion generate
   ```

2. Check for network filesystems (NFS, FUSE). The completer walks
   parent directories for project context, which can be slow on
   network mounts.

## New plugin not showing up

The manifest regenerates automatically for plugins installed via
`conda install` (including `conda-pypi`). For `pip install`:

```bash
conda completion generate
```

## Package or version not showing up

Refresh package metadata from repodata:

```bash
conda completion refresh
```

If you intentionally generated with `--no-repodata`, package name and
version candidates are omitted until you run `conda completion generate`
again without that flag.

## Completions work in one shell but not another

Each shell needs its own hook:

```bash
conda completion install bash
conda completion install zsh
conda completion install fish
```

Restart your shell or source the RC file afterward.
