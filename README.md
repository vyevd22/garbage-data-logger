# horrendous data logger thingy

a python CLI tool for logging match data and generating formatted reports. built around a football discord server use case, but the core is just structured data logging with persistent storage and optional AI-generated summaries.
<br>
dont mind me being a football nerd.

## what it does

- logs match details, basic stats, and honourable mentions through a terminal interface (i havent learned anything about user interfaces or CSS or JS yet and i only know very basic HTML so you're not getting anything more advanced from me)
- generates a formatted discord-ready match report automatically
- tracks player statistics across matches in a JSON file
- keeps a full match history with timestamps if you want it for some reason (also in a JSON file)
- optionally uses the anthropic API to generate honourable mention summaries based on a plain text description (if you wanted to do that for some reason but it seems like a waste of money to me)
- (no seriously i spent 5 euros just to test it 😭)

## requirements

- python 3.x
- an anthropic API key (completely optional and not recommended, only needed for AI-generated mentions. works well tho i wont lie)

install dependencies:
```
pip install anthropic python-dotenv
```

## setup (for some reason)

1. just clone the repo
2. create a `.env` file in the project folder with your API key:
```
ANTHROPIC_API_KEY=your_key_here
```
3. run `match logger.py` to log a match
4. run `leaderboard.py` to view all the stats of players you inputted in that match logger.
<br>
if you want you can also take a look at the `match_history.json` file to manually search through previous matches but im too lazy to actually make a more, uhhh... distinguished(?) way to look at it.

## notes

the `.env` file is gitignored. never commit your API key, that's no bueno. stats.json and match_history.json are also gitignored as they contain personal data of mine 👅
<br>
i hope the code is atleast somewhat readable. i tried adding a lot of comments everywhere to explain some things (as if it's not the most basic thing in the world)
<br>
if it wasnt clear by the lack of quality this is just something i made because i was too lazy to have to do it by hand and i decided 'alright why not just add an AI API i might as well'.
