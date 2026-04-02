# horrendous match logger thingy (now with a TUI because it looks cooler duh)
a python TUI tool for logging football match data and generating formatted discord reports. built around a football discord server use case.
<br>
dont mind me being a football nerd.

## what it does
- logs match details through a single scrollable form; competition, teams, bonus goals, lineups, scorers, assisters, MOTM, honourable mentions...
- generates a formatted discord-ready match report you can copy straight out of the app
- tracks player stats (appearances, goals, assists, MOTM, clean sheets) across matches in a JSON file
- keeps a full match history with timestamps
- generates a shareable encoded string per match so other people can import your results on their end
- lineup generation from a formation string (e.g. `2-3-1` => 7 player rows. 2+3+1 = 6 but since there's always a GK and he's not part of the formation numbers, the formation is always given a +1. 6 + 1 = 7.)

## requirements
- python 3.x
- textual
- a computer (i think)

install dependencies:
```
pip install textual
```
or on arch because that's where i made this (save me):
```
pacman -S python-textual
```

## how to run
```
python app.py
```
that's it. navigate with arrow keys + enter, escape to go back.
OH, just like, make sure you actually cd to the directory you have the git cloned in, lol.

## notes
`stats.json` and `match_history.json` are gitignored since they contain personal data.
<br>
the share code is a compressed + base64 encoded JSON blob. completely local, no servers involved, because i dont know enough about that yet (and it seems like a waste of time)

---

*hey. your dad here. i read every single line of this and i have no idea what half of it does — but i'm proud of you. you built something real, something that works, and you did it on your own. that's not nothing. that's actually everything. keep going.*

*also the match viewer wasn't actually opening in the browser like your readme says it does. fixed it for you. you're welcome.*

*— Dad*

---

im keeping this here i dont care. even tho i changed the whole thing just now.
