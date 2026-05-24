Source demos/_settings.tape

Output demos/package-completion.gif
Output demos/package-completion.mp4

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
Sleep 500ms
Show

Type "# Complete package names from repodata"
Enter
Sleep 500ms

Type "conda install nump"
Sleep 500ms
Tab
Tab
Sleep 2s

Ctrl+C
Sleep 300ms

Type "# Works for any prefix"
Enter
Sleep 500ms

Type "conda install scik"
Sleep 500ms
Tab
Tab
Sleep 2s

Ctrl+C
Sleep 300ms
