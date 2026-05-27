Source demos/_settings.tape

Output demos/repodata-controls.gif
Output demos/repodata-controls.mp4

Hide
Type `eval "$(pixi shell-hook -s bash -e dev)"`
Enter
Wait /\)/
Type `export PS1="$DEMO_PS1"`
Enter
Wait /\$/
Type "clear"
Enter
Wait /\$/
Sleep 500ms
Show

Type "# Generate command completions without repodata"
Enter
Sleep 500ms

Type@80ms "conda completion generate --no-repodata"
Enter
Sleep 2s

Type "# Inspect cache status"
Enter
Sleep 500ms

Type@80ms "conda completion status"
Enter
Sleep 3s

Type "# Force a package metadata refresh when needed"
Enter
Sleep 500ms

Type@80ms "conda completion refresh"
Enter
Sleep 2s
Ctrl+C
