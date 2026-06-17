Set Shell "fish"
Set FontFamily "JetBrains Mono"
Set FontSize 20
Set Width 1200
Set Height 600
Set Margin 20
Set MarginFill "#19191b"
Set Padding 20
Set Theme "Dark+"
Set TypingSpeed 40ms
Set WaitTimeout 120s

Env BAT_OPTS "--color=always --paging=never --plain"
Env BAT_THEME "Visual Studio Dark+"
Env PYTHONWARNINGS "ignore::SyntaxWarning"

Output demos/fish-completion.gif

Hide
Type "pixi shell-hook -s fish -e dev | source"
Enter
Wait /\)/
Type "function fish_prompt; set_color -o green; echo -n '% '; set_color normal; end"
Enter
Wait /%/
Type "function fish_right_prompt; end; set -g fish_autosuggestion_enabled 0; set -g fish_pager_color_description brblack; set -g fish_pager_color_prefix green --bold"
Enter
Wait /%/
Type "conda completion generate --no-repodata > /dev/null 2>&1"
Enter
Wait /%/
Type "complete -c conda -e"
Enter
Wait /%/
Type "conda completion init fish | source"
Enter
Wait /%/
Type "clear"
Enter
Wait /%/
Sleep 500ms
Show

Type "# Fish uses the same conda-completion hook"
Enter
Sleep 500ms

Type "conda completion install --"
Sleep 500ms
Tab
Tab
Sleep 2s

Ctrl+C
Sleep 300ms

Type "# Short descriptions stay readable"
Enter
Sleep 500ms

Type "conda completion uninstall --"
Sleep 500ms
Tab
Tab
Sleep 2s

Ctrl+C
Sleep 300ms
