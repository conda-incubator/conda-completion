Source demos/_settings.tape

Output demos/option-completion.gif
Output demos/option-completion.mp4

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

Type "# Complete flags with descriptions"
Enter
Sleep 500ms

Type "conda install --"
Sleep 500ms
Tab
Tab
Sleep 2s

Ctrl+C
Sleep 300ms

Type "# Complete workspace install flags"
Enter
Sleep 500ms

Type "conda workspace install --"
Sleep 500ms
Tab
Tab
Sleep 2s

Ctrl+C
Sleep 300ms
