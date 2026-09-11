Source demos/_settings.tape

Output demos/workspace-completion.gif

Hide
Type `eval "$(pixi shell-hook -s bash -e dev)"`
Enter
Wait /\)/
Type "conda completion generate --no-repodata > /dev/null 2>&1"
Enter
Wait /\$/
Type `export PS1="$DEMO_PS1" && eval "$(conda completion init bash)"`
Enter
Wait /\$/
Type `DEMO_TMPDIR=$(mktemp -d "${TMPDIR:-/tmp}/conda-completion-demo.XXXXXX") || exit 1`
Enter
Wait /\$/
Type `trap 'rm -rf -- "$DEMO_TMPDIR"' EXIT`
Enter
Wait /\$/
Type `mkdir "$DEMO_TMPDIR/project" && cp demos/fixtures/conda.toml "$DEMO_TMPDIR/project/"`
Enter
Wait /\$/
Type `mkdir -p "$DEMO_TMPDIR/home/.conda" && printf '/opt/conda/envs/base\n/opt/conda/envs/data-science\n/opt/conda/envs/web-dev\n' > "$DEMO_TMPDIR/home/.conda/environments.txt" && export HOME="$DEMO_TMPDIR/home"`
Enter
Wait /\$/
Type `cd "$DEMO_TMPDIR/project"`
Enter
Wait /\$/
Type "clear"
Enter
Wait /\$/
Sleep 500ms
Show

Type "# Show the workspace manifest"
Enter
Sleep 500ms

Type@80ms "bat conda.toml"
Enter
Sleep 1s

Type "# Complete workspace environments"
Enter
Sleep 500ms

Type "conda workspace install -e "
Sleep 500ms
Tab
Tab
Sleep 2s

Ctrl+C
Sleep 300ms

Type "# Complete channels from workspace"
Enter
Sleep 500ms

Type "conda install --channel "
Sleep 500ms
Tab
Sleep 2s

Ctrl+C
Sleep 300ms
