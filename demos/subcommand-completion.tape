Source demos/_settings.tape

Output demos/subcommand-completion.gif
Output demos/subcommand-completion.mp4

Hide
Type `eval "$(pixi shell-hook -s bash -e dev)"`
Enter
Wait /\)/
Type `export PS1="$DEMO_PS1" && eval "$(conda completion init bash)"`
Enter
Wait /\$/
Type "clear"
Enter
Wait /\$/
Show

Type "# Complete conda subcommands"
Enter
Sleep 500ms

Type "conda "
Sleep 500ms
Tab
Tab
Sleep 2s

Ctrl+C
Sleep 300ms

Type "# Complete workspace subcommands"
Enter
Sleep 500ms

Type "conda workspace "
Sleep 500ms
Tab
Tab
Sleep 2s

Ctrl+C
Sleep 300ms

Type "# Complete self subcommands"
Enter
Sleep 500ms

Type "conda self "
Sleep 500ms
Tab
Tab
Sleep 2s

Ctrl+C
Sleep 300ms
