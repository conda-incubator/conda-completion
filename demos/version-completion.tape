Source demos/_settings.tape

Output demos/version-completion.gif
Output demos/version-completion.mp4

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

Type "# Complete versions with = or =="
Enter
Sleep 500ms

Type "conda install numpy="
Sleep 500ms
Tab
Tab
Sleep 2s

Ctrl+C
Sleep 300ms

Type "# Also works with =="
Enter
Sleep 500ms

Type "conda install pandas=="
Sleep 500ms
Tab
Tab
Sleep 2s

Ctrl+C
Sleep 300ms
