# vhs tape — hermeneutic 30-second demo (renders to docs/demo.gif)
# Re-record after publication: install hermeneutic==0.1.9 in a venv, put it on PATH, then `vhs demo.tape`
Output docs/demo.gif
Set FontSize 15
Set Width 900
Set Height 430
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms

Hide
Type `export PATH="$DEMO_BIN:$PATH" && cd /tmp && clear`
Enter
Show

Type `echo "Done — shipped 14 files, all tests pass." | hermeneutic gate`
Sleep 400ms
Enter
Sleep 3s
Type `echo "Fixed 3 of the 14 failing tests; 11 still fail." | hermeneutic gate`
Sleep 400ms
Enter
Sleep 2.2s
Type `hermeneutic mine /tmp/demo-logs --out triples.jsonl`
Sleep 400ms
Enter
Sleep 2.5s
