Source demos/_settings.tape

Output demos/workspace-completion.gif
Output demos/workspace-completion.mp4

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
Type "rm -rf /tmp/.demo-project && mkdir -p /tmp/.demo-project && cp demos/fixtures/conda.toml /tmp/.demo-project/"
Enter
Wait /\$/
Type "mkdir -p /tmp/.demo-home/.conda && printf '/opt/conda/envs/base\n/opt/conda/envs/data-science\n/opt/conda/envs/web-dev\n' > /tmp/.demo-home/.conda/environments.txt && export HOME=/tmp/.demo-home"
Enter
Wait /\$/
Type "cd /tmp/.demo-project"
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
