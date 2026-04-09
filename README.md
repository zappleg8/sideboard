# Sideboard

**Chess in your terminal. Play against Chesster while your coding agent thinks.**

```
    a   b   c   d   e   f   g   h
  +---+---+---+---+---+---+---+---+
8 | r | n | b | q | k | b | n | r | 8
  +---+---+---+---+---+---+---+---+
7 | p | p |   | p | p | p | p | p | 7
  +---+---+---+---+---+---+---+---+
6 |   |   |   |   |   |   |   |   | 6
  +---+---+---+---+---+---+---+---+
5 |   |   | p |   |   |   |   |   | 5
  +---+---+---+---+---+---+---+---+
4 |   |   |   |   | P |   |   |   | 4
  +---+---+---+---+---+---+---+---+
3 |   |   |   |   |   | N |   |   | 3
  +---+---+---+---+---+---+---+---+
2 | P | P | P | P |   | P | P | P | 2
  +---+---+---+---+---+---+---+---+
1 | R | N | B | Q | K | B |   | R | 1
  +---+---+---+---+---+---+---+---+
    a   b   c   d   e   f   g   h

Chesster: The Sicilian! Bold choice. I see you like to suffer beautifully.
```

Sideboard is a chess game designed to live natively inside coding agent harnesses like [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Play against Chesster -- a witty, overconfident, slightly unhinged AI opponent -- right in your terminal.

## Install

```bash
pip install sideboard
```

## Play

```bash
sideboard                          # new game (default: club difficulty)
sideboard --difficulty casual      # beginner-friendly
sideboard --difficulty shark       # bring your A-game
sideboard --white                  # play as white
sideboard --black                  # play as black
sideboard resume                   # pick up where you left off
sideboard stats                    # your record vs Chesster
```

## Inside Claude Code

```bash
sideboard install-skill
```

Then type `/sideboard` in any Claude Code session. The game launches in your terminal -- play a few moves while you wait, quit with `q`, and you're right back to coding.

For the full experience, try `/sideboard ai` -- Claude becomes Chesster and plays you conversationally.

## How It Works

**Terminal mode** launches a Rich-powered chess TUI. You play against a local minimax engine with alpha-beta pruning. Chesster provides commentary via curated quips that react to your moves.

**Subagent mode** turns Claude into Chesster. The LLM picks moves from engine suggestions and adds real personality -- dynamic banter, opening opinions, genuine reactions. The game logic stays correct via python-chess.

## In-Game Commands

| Command | What it does |
|---------|-------------|
| `q` | Resign and exit |
| `draw` | Offer a draw (Chesster decides) |
| `undo` | Take back your last move |
| `pgn` | Show the game notation |
| `flip` | Flip the board |
| `help` | Show commands |

Moves use standard algebraic notation: `e4`, `Nf3`, `O-O`, `Bxe5`, `e8=Q`.

## Dependencies

Just two:
- [python-chess](https://python-chess.readthedocs.io/) -- the chess brain
- [Rich](https://rich.readthedocs.io/) -- the beautiful terminal output

## License

MIT
