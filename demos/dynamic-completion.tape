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
Type "rm -rf /tmp/.demo-project && mkdir -p /tmp/.demo-project && cp demos/fixtures/environment.yml /tmp/.demo-project/"
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

Type "# Show the project file"
Enter
Sleep 500ms

Type@80ms "bat environment.yml"
Enter
Sleep 1s

Type "# Complete environment name from project"
Enter
Sleep 500ms

Type "conda create -n "
Sleep 500ms
Tab
Tab
Sleep 2s

Ctrl+C
Sleep 300ms

Type "# Complete channels from project"
Enter
Sleep 500ms

Type "conda install --channel "
Sleep 500ms
Tab
Tab
Sleep 2s

Ctrl+C
Sleep 300ms
