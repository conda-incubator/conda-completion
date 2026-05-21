# Shell support

conda-completion uses a tiered support model.

## Support tiers

**Tier 1** shells are fully tested in CI on every push and actively
maintained by the project.

**Tier 2** shells are community-tested and maintained on a best-effort
basis. Bug reports and contributions are welcome.

## Feature matrix

| Feature | bash | zsh | PowerShell | fish |
|---|---|---|---|---|
| **Tier** | 1 | 1 | 1 | 2 |
| Command completion | Yes | Yes | Yes | Yes |
| Flag completion | Yes | Yes | Yes | Yes |
| Flag value completion | Yes | Yes | Yes | Yes |
| Descriptions | No | Yes | Yes | Yes |
| `install`/`uninstall` | Yes | Yes | Yes | Yes |
| Dynamic env names | Yes | Yes | Yes | Yes |
| Dynamic channels | Yes | Yes | Yes | Yes |
| Dynamic task names | Yes | Yes | Yes | Yes |

## RC file locations

| Shell | RC file(s) |
|---|---|
| bash | `~/.bashrc`, `~/.bash_profile` |
| zsh | `~/.zshrc` |
| PowerShell (Windows) | `~/Documents/PowerShell/Microsoft.PowerShell_profile.ps1` |
| PowerShell (macOS/Linux) | `~/.config/powershell/Microsoft.PowerShell_profile.ps1` |
| fish | `~/.config/fish/config.fish` |

`conda completion install` writes a delimited block to the first existing
RC file (or creates the first one in the list if none exist).

## cmd.exe (Windows)

cmd.exe has no programmable completion API. Unlike bash, zsh, fish, and
PowerShell, there is no way to register a custom completer for a
command. cmd.exe's built-in TAB completion only cycles through file and
directory names.

Windows users who want conda tab completion should use PowerShell,
which is installed by default on all modern Windows versions.

## Future Tier 2 candidates

The following shells have programmable completion APIs and are
candidates for future Tier 2 support. Contributions are welcome.

**xonsh**
: A Python-powered shell with a `completes_for` decorator for
  registering custom completers. conda supports xonsh in `conda init`,
  and mamba supports it in `shell completion`. xonsh is particularly
  relevant to conda's audience given its Python roots.

**Nushell**
: A modern structured-data shell with an `extern` completion system.
  Growing in popularity, already supported by `argc-completions`.
  Nushell uses tab-separated output similar to fish, so the Rust
  binary's output format may need only minor adaptation.

**tcsh**
: A legacy C shell with a `complete` builtin for programmable
  completions. conda supports tcsh in `conda init`. Still ships as the
  default root shell on some BSDs, though usage is declining.

If you are interested in adding support for one of these shells, the
main work is writing a shell integration script (similar to the
existing scripts in `conda_completion/shell/` and
`conda_completion/contrib/`) and adding an output format to the Rust
binary if the shell's completion protocol differs from the existing
ones.

## Shell detection

When the shell argument is omitted, conda-completion detects the current
shell:

1. Check the `SHELL` environment variable and extract the basename.
2. If `SHELL` is not set and the platform is Windows, default to
   `powershell`.
3. Otherwise, default to `bash`.
