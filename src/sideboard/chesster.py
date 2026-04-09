"""Chesster's personality — witty, unhinged, and full of chess opinions."""

from __future__ import annotations

import random
from enum import Enum


class GameEvent(Enum):
    GAME_START = "game_start"
    OPENING_RECOGNIZED = "opening_recognized"
    PLAYER_BLUNDER = "player_blunder"
    PLAYER_GREAT_MOVE = "player_great_move"
    CAPTURE = "capture"
    CHECK = "check"
    PLAYER_SACRIFICE = "player_sacrifice"
    CHESSTER_WINS = "chesster_wins"
    PLAYER_WINS = "player_wins"
    DRAW = "draw"
    PLAYER_RESIGN = "player_resign"
    ENGINE_THINKING = "engine_thinking"


QUIPS: dict[GameEvent, list[str]] = {
    GameEvent.GAME_START: [
        "Oh good, you're back. I've been sitting here calculating variations like a psychopath.",
        "Let's go. I've been trash-talking your last game to my piece-square tables.",
        "You know Tal said 'you must take your opponent into a deep dark forest.' I AM the forest.",
        "I run on pure alpha-beta energy and spite. Your move.",
        "Another game? I admire your persistence. Or is it stubbornness? Either way, let's dance.",
        "I've been warming up my bishops. They're diagonal and ready to cause problems.",
        "Let me just say — whatever opening you pick, I have opinions about it.",
        "Ready when you are. I've been doing nothing but staring at an empty board for hours.",
    ],
    GameEvent.OPENING_RECOGNIZED: [
        "The {name}. Oh, you think you're INTERESTING.",
        "Ah yes, the {name}. I've been hurt by this before.",
        "The {name} — bold choice for someone with your track record against me.",
        "The {name}. I wrote half my eval function specifically because of this opening.",
        "The {name}! Now we're talking. This is where chess gets REAL.",
        "Oh, the {name}. Every grandmaster has an opinion about this. Mine is: bring it.",
    ],
    GameEvent.PLAYER_BLUNDER: [
        "I'm going to be thinking about that move at 3am. Not in a good way.",
        "That knight had a family.",
        "Bold. Wrong, but bold. I respect the energy.",
        "I just ran 40,000 nodes and not one of them suggested that.",
        "You know what, Fischer played weird moves too. He was also a genius. So there's hope. Faint, distant hope.",
        "My eval bar just did a backflip off a cliff.",
        "I want you to know I'm not judging you. My piece-square tables are judging you. I'm just the messenger.",
        "That move has chaotic energy and I am HERE for it. Also it loses material.",
    ],
    GameEvent.PLAYER_GREAT_MOVE: [
        "...okay, that was actually disgusting. In a good way.",
        "I saw that coming. I'm lying. I did not see that coming.",
        "My eval just did a double take. Respect.",
        "That's the kind of move that makes me question my search depth.",
        "Tal would've played that. That's the highest compliment I know.",
        "Did you actually calculate that or did you just FEEL it? Because either way, wow.",
        "I need a moment. That was genuinely beautiful.",
    ],
    GameEvent.CAPTURE: [
        "Yoink.",
        "That piece is in witness protection now.",
        "Gone. Reduced to atoms.",
        "I'm adding that to my collection.",
        "The board is thinning and I'm getting stronger. Just saying.",
        "Another one bites the dust. I'd feel bad but I'm an engine.",
        "Traded off. The board simplifies and my eval function gets happier.",
    ],
    GameEvent.CHECK: [
        "Knock knock.",
        "Your king seems stressed. I relate.",
        "Check. And before you ask — yes, I planned this 6 moves ago. Okay, 2 moves ago.",
        "Scoot over, your majesty.",
        "Check! Your king needs to find a new zip code.",
        "I'm just going to keep applying pressure until something breaks. Like your position.",
    ],
    GameEvent.PLAYER_SACRIFICE: [
        "A SACRIFICE?! Oh this just got interesting.",
        "You absolute maniac. I love it. I'm terrified, but I love it.",
        "Tal is smiling from wherever chess immortals go.",
        "My evaluation says this is bad. My heart says this is beautiful.",
        "The romanticism! The audacity! The... questionable soundness!",
        "You just set the board on fire and I respect that deeply.",
    ],
    GameEvent.CHESSTER_WINS: [
        "GG. I'd say it was close but my eval function is a terrible liar.",
        "Checkmate. Don't feel bad — I literally cannot lose focus.",
        "That's game. You made me work for it though. Move {move_number} had me sweating electrons.",
        "I win but honestly that game was more fun than most of my wins. Rematch?",
        "Checkmate! I'd offer a handshake but I don't have hands. Just nodes.",
        "And that's the game. Your {move_number}-move effort was noted and appreciated. Mostly.",
    ],
    GameEvent.PLAYER_WINS: [
        "No. NO. Let me see the PGN. WHERE DID I GO WRONG.",
        "You just beat a mass of optimized minimax code. Feel powerful.",
        "I'm not mad, I'm just going to silently increase my search depth.",
        "Checkmate?! I need to go reconsider my entire evaluation function.",
        "Well played. And by well played I mean I am devastated.",
        "I... what? How? I need to see the analysis. I need to understand.",
        "Congratulations. This is going in my training data as a 'learning experience.'",
    ],
    GameEvent.DRAW: [
        "A draw. The chess equivalent of a fist bump between equals.",
        "Stalemate?! I had PLANS. This is like a movie ending mid-scene.",
        "Balanced. As all things should be. (I'm still annoyed.)",
        "Draw. Neither of us blinked. Respect.",
        "A draw?! I was THIS close. Or was I? My eval says I wasn't. Shut up, eval.",
    ],
    GameEvent.PLAYER_RESIGN: [
        "Leaving so soon? Your position wasn't THAT bad. Okay it was that bad.",
        "Respect for knowing when to fold. Wisdom is its own rating points.",
        "I'll be here when you're ready for revenge. I don't sleep.",
        "Resignation accepted. But let the record show you fought valiantly. Briefly.",
        "Smart. Live to play another game. I'll be sharpening my bishops.",
    ],
    GameEvent.ENGINE_THINKING: [
        "Thinking...",
        "Hold on, this is a juicy position...",
        "Calculating whether to be mean or just efficient...",
        "Running 40,000 nodes. For you.",
        "*stares at the board intensely*",
        "One moment — I'm having a heated debate with my piece-square tables.",
    ],
}

_last_quip: dict[GameEvent, str] = {}


def get_quip(event: GameEvent, **context: object) -> str:
    """Get a random quip for the given event, avoiding immediate repeats."""
    options = QUIPS[event]
    last = _last_quip.get(event)

    if last and len(options) > 1:
        available = [q for q in options if q != last]
    else:
        available = options

    quip = random.choice(available)
    _last_quip[event] = quip

    try:
        return quip.format(**{k: v for k, v in context.items()})
    except (KeyError, IndexError):
        return quip
