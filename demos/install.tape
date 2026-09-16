Source demos/_settings.tape

Output demos/install.gif

Hide
Type `eval "$(pixi shell-hook -s bash -e dev)"`
Enter
Wait /\)/
Type `export PS1="$DEMO_PS1" && export SHELL=/bin/bash`
Enter
Wait /\$/
Type `DEMO_TMPDIR=$(mktemp -d "${TMPDIR:-/tmp}/conda-completion-demo.XXXXXX") || exit 1`
Enter
Wait /\$/
Type `trap 'rm -rf -- "$DEMO_TMPDIR"' EXIT`
Enter
Wait /\$/
Type `mkdir "$DEMO_TMPDIR/home" && touch "$DEMO_TMPDIR/home/.bashrc" && export HOME="$DEMO_TMPDIR/home"`
Enter
Wait /\$/
Type "conda completion generate --no-repodata > /dev/null 2>&1"
Enter
Wait /\$/
Type "clear"
Enter
Wait /\$/
Sleep 500ms
Show

Type "# Preview what install will do"
Enter
Sleep 500ms

Type@80ms "conda completion install --dry-run"
Enter
Sleep 2s

Type "# Install the completion hook"
Enter
Sleep 500ms

Type@80ms "conda completion install --yes --no-repodata"
Enter
Sleep 2s

Type "# Verify the hook was added"
Enter
Sleep 500ms

Type@80ms "grep -A2 'conda-completion' ~/.bashrc"
Enter
Sleep 1s

Type "# Uninstall when you're done"
Enter
Sleep 500ms

Type@80ms "conda completion uninstall --yes"
Enter
Sleep 1s
