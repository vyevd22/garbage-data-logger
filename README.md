# horrendous data logger thingy
a python CLI tool for logging match data and generating formatted reports. built around a football discord server use case, but the core is just structured data logging with persistent storage and optional AI-generated summaries.
<br>
dont mind me being a football nerd.

## what it does
- logs match details, basic stats, and honourable mentions through a terminal interface
- generates a formatted discord-ready match report automatically
- tracks player statistics across matches in a JSON file
- keeps a full match history with timestamps (also in a JSON file)
- optionally uses the anthropic API to generate honourable mention summaries based on a plain text description (if you wanted to do that for some reason but it seems like a waste of money to me)
- (no seriously i spent 5 euros just to test it 😭)
- generates a pretty (not really) HTML match report viewer from your match history, with a formation display and everything (its literally built with the most basic css and html you'll find)

## requirements
- python 3.x
- an anthropic API key (completely optional and not recommended, only needed for AI-generated mentions. works well tho i wont lie)

install dependencies:
```
pip install anthropic python-dotenv
```

## setup (if you, for some reason, felt the need to try out something this boring)
1. just clone the repo
2. create a `.env` file in the project folder with your API key:
```
ANTHROPIC_API_KEY=your_key_here
```
3. run `match logger.py` to log a match
4. run `leaderboard.py` to view all the stats of players you inputted in that match logger
5. run `match viewer.py` to generate an HTML report of your most recent match — opens in any browser

## notes
the `.env` file is gitignored. never commit your API key, that's no bueno. stats.json, match_history.json, and any generated .html files are also gitignored as they contain personal data of mine 👅
<br>
i hope the code is atleast somewhat readable. i tried adding a lot of comments everywhere to explain some things (as if it's not the most basic thing in the world but whatever)
<br>
if it wasnt clear by the lack of quality this is just something i made because i was too lazy to have to do it by hand and i decided 'alright why not just add an AI API i might as well'.
<br>
i suck at programming
