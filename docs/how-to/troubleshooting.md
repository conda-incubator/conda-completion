# Troubleshooting

## Completions stopped working

The completion manifest is stale or missing. Regenerate it:

```bash
conda completion generate
```

If completions still don't work after regenerating, check that the shell hook is installed:

```bash
conda completion status
```

## "Completion data not found"

This error means the manifest file does not exist. This happens on first install or if the cache was cleared.

```bash
conda completion generate
conda completion install
```

## "Completion engine binary not found"

The `conda-completer` package is not installed or cannot be located.

```bash
conda install conda-completer
```

If `conda-completer` is installed but the error persists, run `conda completion status` to verify the binary path.

## "Cannot read completion data"

The manifest file is corrupt. Delete it and regenerate:

```bash
rm "$(conda completion status 2>&1 | grep Manifest: | awk '{print $2}')"
conda completion generate
```

## "Shell 'X' is not supported"

You passed an unsupported shell name to `install` or `init`. Supported shells:

- **Tier 1** (fully tested in CI): `bash`, `zsh`, `powershell`
- **Tier 2** (community-tested): `fish`

## Completions are slow

If tab completion takes more than 200 ms:

1. Regenerate the manifest to pick up any format improvements:

   ```bash
   conda completion generate
   ```

2. Check if you are working on a network filesystem (NFS, FUSE). The completer walks parent directories to find project context. On network mounts this can be slow. Move your working directory closer to the project root.

3. Run `conda completion status` to check the manifest size. If the versions data is in legacy format (single file > 2 MB), regenerating will produce the faster indexed format.

## New plugin not showing up in completions

The manifest needs to be regenerated after installing new conda plugins. This happens automatically for plugins installed via `conda install`, but not for plugins installed via `pip install` directly.

```bash
conda completion generate
```

If you installed a plugin with `conda-pypi`, the manifest is regenerated automatically because `conda-pypi` runs as part of `conda install`.

## Tab completion works in one shell but not another

Each shell needs its own hook installed. Check which shell you are running and install the hook:

```bash
conda completion install bash
conda completion install zsh
conda completion install fish
```

After installing, restart your shell or source the RC file as instructed.
