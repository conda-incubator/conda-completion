Source demos/_settings.tape

Output demos/fuzzy-matching.gif
Output demos/fuzzy-matching.mp4

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

Type "# Fuzzy matching handles typos"
Enter
Sleep 500ms

Type "conda install numpie"
Sleep 1s
Tab
Sleep 1s
Tab
Sleep 2s

Ctrl+C
Sleep 300ms

Type "# Transpositions too"
Enter
Sleep 500ms

Type "conda install nupmy"
Sleep 1s
Tab
Sleep 1s
Tab
Sleep 2s

Ctrl+C
Sleep 300ms

Type "# Wrong separator"
Enter
Sleep 500ms

Type "conda install scikit_learn"
Sleep 1s
Tab
Sleep 1s
Tab
Tab
Sleep 3s

Ctrl+C
Sleep 300ms
