Source demos/_settings.tape

Output demos/install.gif
Output demos/install.mp4

Hide
Type `eval "$(pixi shell-hook -s bash -e dev)"`
Enter
Wait /\)/
Type `export PS1="$DEMO_PS1" && export SHELL=/bin/bash && rm -rf /tmp/.demo-home && mkdir -p /tmp/.demo-home && touch /tmp/.demo-home/.bashrc && export HOME=/tmp/.demo-home`
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
