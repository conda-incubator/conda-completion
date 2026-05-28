# Troubleshooting

For a step-by-step debugging workflow, see
{doc}`diagnose-and-repair`.

## Completions stopped working

Regenerate the manifest:

```bash
conda completion generate
```

If that doesn't help, check that the shell hook is installed:

```bash
conda completion status
conda completion install --dry-run
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

Use the cache directory printed by `conda completion status`, remove
`completion.msgpack`, and run `conda completion generate`. See
{doc}`diagnose-and-repair` for platform-specific commands.

## "Shell 'X' is not supported"

Unsupported shell name passed to `install` or `init`. Supported:

- `bash`
- `zsh`
- `powershell`
- `fish`

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

After `conda install`, `conda remove`, or `conda update`,
conda-completion regenerates the manifest when registered conda entry
point names changed. For plugins installed outside conda's package
manager, or plugin updates that only changed argparse metadata:

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

Package completion also requires a non-empty package prefix. Use
`conda install num<TAB>`, not `conda install <TAB>`, when you want package
name candidates.

## Completions work in one shell but not another

Each shell needs its own hook:

```bash
conda completion install zsh
```

Run the command once for the shell that is missing completions. Use
`bash`, `zsh`, `powershell`, or `fish` as the shell argument.

Restart your shell or source the RC file afterward.

## Completions work in a normal terminal but not in an IDE

The IDE terminal is probably not reading the same startup file. Check the
configured shell path in the IDE and install the hook for that shell, or
add the manual hook to the file it loads.

See {doc}`nonstandard-shell-startup` and
{doc}`remote-and-automated-environments`.
