# Errors

All conda-completion errors inherit from conda's `CondaError` base
class and include hints. For step-by-step solutions, see
{doc}`/how-to/troubleshooting`.

## Error types

### ManifestNotFoundError

```text
Completion data not found
  hint: Run 'conda completion generate' to create it
```

The manifest file does not exist. Happens on first install, after
clearing the cache, or if the cache directory was moved.

Fix: `conda completion generate`

### ManifestError

```text
Cannot read completion data: <details>
  hint: Try regenerating with 'conda completion generate'
  hint: If the problem persists, remove the file and regenerate
```

The manifest exists but cannot be deserialized. Causes: corrupt file
(partial write, disk error), incompatible format version, or the file
is not a msgpack mapping.

Fix: `conda completion generate`. If that fails, delete the manifest
manually (run `conda completion status` to find the path) and
regenerate.

### IntrospectionError

```text
Cannot inspect conda commands: <details>
  hint: Check whether a conda plugin fails to import
  hint: Disable or update the failing plugin, then run 'conda completion generate'
```

conda's parser could not be generated or walked during
`conda completion generate`. This usually means conda itself or a conda
plugin raised an exception while registering commands.

Fix: run `conda completion generate` again after disabling, updating,
or removing the failing plugin.

### CompleterBinaryNotFoundError

```text
Completion engine binary not found
  hint: Reinstall conda-completer: conda install conda-completer
  hint: For development: pixi run build
```

The `_conda_completer` Rust binary is not installed or cannot be
located.

Fix: `conda install conda-completer`. For development installs,
`pixi run build`.

### ShellNotSupportedError

```text
Shell 'nushell' is not supported
  hint: Supported shells: bash, fish, powershell, zsh
```

An unrecognized shell name was passed to `install`, `uninstall`, or
`init`.

### CondaCompletionError

Base class for all conda-completion errors. Not raised directly.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Error (one of the above, or unhandled exception) |

`conda completion` catches all `CondaCompletionError` exceptions, logs
the message and hints, and returns exit code 1.

## Rust binary errors

The Rust binary (`_conda_completer`) writes errors to stderr and exits
with code 1. These are not normally visible because the shell completion
script captures stdout only.

```text
Usage: _conda_completer --shell <shell> --manifest <path> [--versions <path>] -- <words...> <cword>
```

Printed when required arguments are missing.

```text
Failed to load manifest: <details>
```

The manifest could not be read or deserialized. Same causes as
`ManifestError`.
