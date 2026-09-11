Source demos/_settings.tape

Output demos/quickstart.gif

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
Type "conda completion generate > /dev/null 2>&1"
Enter
Wait /\$/
Type `eval "$(conda completion init bash)"`
Enter
Wait /\$/
Type "clear"
Enter
Wait /\$/
Sleep 500ms
Show

Type "# Install completion for your shell"
Enter
Sleep 500ms

Type@80ms "conda completion install --yes"
Enter
Sleep 2s

Type "# Try it -- complete subcommands"
Enter
Sleep 500ms

Type "conda ins"
Sleep 500ms
Tab
Sleep 1s

Ctrl+C
Sleep 300ms

Type "# Complete flags"
Enter
Sleep 500ms

Type "conda install --"
Sleep 500ms
Tab
Tab
Sleep 2s

Ctrl+C
Sleep 300ms
