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
| Package name completion | Yes | Yes | Yes | Yes |
| Version completion (`=`) | Yes | Yes | Yes | Yes |
| Fuzzy matching | Yes | Yes | Yes | Yes |
| Descriptions | No | Yes | Yes | Yes |
| `install`/`uninstall` | Yes | Yes | Yes | Yes |
| Dynamic env names | Yes | Yes | Yes | Yes |
| Dynamic channels | Yes | Yes | Yes | Yes |
| Dynamic task names | Yes | Yes | Yes | Yes |

## Shell-specific behavior

Each shell has different completion mechanics. The generated scripts
handle these differences so completions work consistently across shells.

**Completion ordering.** conda-completion returns results in a specific
order: package names sorted by length (shortest first), versions sorted
newest-first. Without shell-specific handling, some shells re-sort
results alphabetically:

- **bash**: `compopt -o nosort` (bash 4.4+) prevents re-sorting
- **zsh**: `_describe -V` creates an unsorted completion group
- **fish**: `complete -k` keeps insertion order
- **PowerShell**: preserves order by default

**Equals sign in version specs.** Typing `conda install numpy=1.26`
requires the shell to treat `numpy=1.26` as a single token. Bash splits
on `=` by default via `COMP_WORDBREAKS`, so the generated bash script
removes `=` from that variable. Other shells do not split on `=`.

**Descriptions.** Zsh, fish, and PowerShell display descriptions
alongside completion candidates. Bash's COMPREPLY does not support
descriptions, so the Rust binary omits them for bash output.

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
shell using this priority order:

1. `CONDA_COMPLETION_SHELL` environment variable (explicit override).
2. Process tree walking: walks parent processes via `ps` to find the
   nearest shell. This correctly detects shells like fish even when
   they are not the login shell (where `$SHELL` would still point to
   the login shell). Works on Linux, macOS, WSL, and Git Bash/MSYS2.
   Falls through silently on native Windows where `ps` is unavailable.
3. `SHELL` environment variable (extracts the basename).
4. Platform default: `powershell` on Windows, `bash` otherwise.

The process tree approach is inspired by
[shellingham](https://github.com/sarugaku/shellingham) (ISC license).
