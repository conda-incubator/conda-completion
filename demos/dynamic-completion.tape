Source demos/_settings.tape

Output demos/dynamic-completion.gif
Output demos/dynamic-completion.mp4

Hide
Type `eval "$(pixi shell-hook -s bash -e dev)"`
Enter
Wait /\)/
Type `export PS1="$DEMO_PS1" && eval "$(conda completion init bash)"`
Enter
Wait /\$/
Type "rm -rf /tmp/.demo-project && mkdir -p /tmp/.demo-project && cp demos/fixtures/conda.toml /tmp/.demo-project/"
Enter
Wait /\$/
Type "cd /tmp/.demo-project"
Enter
Wait /\$/
Type "clear"
Enter
Wait /\$/
Show

Type "# Show the project file"
Enter
Sleep 500ms

Type@80ms "bat conda.toml"
Enter
Sleep 1s

Type "# Complete environment names from conda.toml"
Enter
Sleep 500ms

Type "conda workspace install -e "
Sleep 500ms
Tab
Tab
Sleep 2s

Ctrl+C
Sleep 300ms

Type "# Complete task names from conda.toml"
Enter
Sleep 500ms

Type "conda task run "
Sleep 500ms
Tab
Tab
Sleep 2s

Ctrl+C
Sleep 300ms
