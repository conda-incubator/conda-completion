Source demos/_settings.tape

Output demos/quickstart.gif
Output demos/quickstart.mp4

Hide
Type `eval "$(pixi shell-hook -s bash -e dev)"`
Enter
Wait /\)/
Type `export PS1="$DEMO_PS1" && export SHELL=/bin/bash && rm -rf /tmp/.demo-home && mkdir -p /tmp/.demo-home && touch /tmp/.demo-home/.bashrc && export HOME=/tmp/.demo-home`
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
