"""Main game loop — the orchestrator that ties everything together."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import chess
from rich.console import Console
from rich.text import Text

from sideboard.board import render_screen, format_move_list
from sideboard.chesster import GameEvent, get_quip
from sideboard.engine import best_move, evaluate, top_moves
from sideboard.state import (
    DEFAULT_DATA_DIR,
    GameState,
    delete_current_game,
    export_pgn,
    load_game,
    load_stats,
    record_result,
    save_game,
    save_pgn,
)

# Known openings (small set for v1 — just the popular ones)
_OPENINGS: dict[str, str] = {
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq": "King's Pawn Opening",
    "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq": "Queen's Pawn Opening",
    "rnbqkbnr/pppppppp/8/8/2P5/8/PP1PPPPP/RNBQKBNR b KQkq": "English Opening",
    "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq": "Sicilian Defense",
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq": "Open Game",
    "rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq": "French Defense",
    "rnbqkbnr/pppppp1p/6p1/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq": "Modern Defense",
    "rnbqkb1r/pppppppp/5n2/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq": "Alekhine's Defense",
    "rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq": "Caro-Kann Defense",
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3": "King's Pawn Opening",
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq": "King's Knight Opening",
    "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq": "Italian / Ruy Lopez / Scotch",
    "rnbqkbnr/pppp1ppp/8/4p3/2P5/8/PP1PPPPP/RNBQKBNR w KQkq": "English: Reversed Sicilian",
    "rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq": "Closed Game",
    "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq": "Scandinavian Defense",
    "rnbqkb1r/pppppppp/5n2/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq": "Indian Defense",
    "rnbqkbnr/pppppp1p/6p1/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq": "Modern Defense vs d4",
    "rnbqkb1r/pppppp1p/5np1/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq": "King's Indian Defense",
}

COMMANDS = {"q", "quit", "draw", "undo", "pgn", "flip", "help"}

# Eval change thresholds (centipawns)
BLUNDER_THRESHOLD = 150
GREAT_MOVE_THRESHOLD = 50  # finding the engine's top move in a complex position


@dataclass
class InputResult:
    kind: str  # "move", "command", "error"
    move: chess.Move | None = None
    command: str = ""
    message: str = ""


def parse_input(text: str, board: chess.Board) -> InputResult:
    """Parse user input as a move or command."""
    text = text.strip()

    if text.lower() in COMMANDS:
        cmd = "quit" if text.lower() == "q" else text.lower()
        return InputResult(kind="command", command=cmd)

    # Try to parse as SAN
    try:
        move = board.parse_san(text)
        return InputResult(kind="move", move=move)
    except (chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError):
        pass

    # Try UCI notation as fallback
    try:
        move = board.parse_uci(text)
        if move in board.legal_moves:
            return InputResult(kind="move", move=move)
    except (chess.InvalidMoveError, ValueError):
        pass

    # Build helpful error message
    # Detect what piece they might be trying to move
    piece_char = text[0] if text and text[0].isupper() else None
    piece_type = {
        "N": chess.KNIGHT, "B": chess.BISHOP, "R": chess.ROOK,
        "Q": chess.QUEEN, "K": chess.KING,
    }.get(piece_char)  # type: ignore[arg-type]

    if piece_type:
        legal_for_piece = [
            board.san(m) for m in board.legal_moves
            if board.piece_at(m.from_square)
            and board.piece_at(m.from_square).piece_type == piece_type  # type: ignore[union-attr]
        ]
        if legal_for_piece:
            return InputResult(
                kind="error",
                message=f"Illegal move. Legal {chess.piece_name(piece_type)} moves: {', '.join(legal_for_piece)}",
            )

    # Generic pawn moves
    legal_pawns = [
        board.san(m) for m in board.legal_moves
        if board.piece_at(m.from_square)
        and board.piece_at(m.from_square).piece_type == chess.PAWN  # type: ignore[union-attr]
    ]
    return InputResult(
        kind="error",
        message=f"Illegal move '{text}'. Try SAN notation (e.g. e4, Nf3, O-O). Legal pawn moves: {', '.join(legal_pawns[:8])}",
    )


def detect_opening(board: chess.Board) -> str | None:
    """Try to detect the opening from the current position."""
    if len(board.move_stack) < 2 or len(board.move_stack) > 10:
        return None

    # Check the FEN (without move counters) against known openings
    fen = board.fen()
    # Strip move counters for matching
    fen_key = " ".join(fen.split()[:4])

    return _OPENINGS.get(fen_key)


def detect_event(
    board: chess.Board,
    last_move: chess.Move | None,
    *,
    eval_before: int,
    eval_after: int,
    is_player_move: bool = False,
) -> GameEvent | None:
    """Detect what kind of event just happened for Chesster's commentary.

    eval_before / eval_after are always from White's perspective (positive =
    White is winning).  is_player_move must be True when the move was made by
    the human player so that PLAYER_BLUNDER / PLAYER_GREAT_MOVE /
    PLAYER_SACRIFICE can fire.
    """
    if last_move is None:
        return None

    if board.is_checkmate():
        # Caller determines chesster_wins vs player_wins
        return None

    if board.is_game_over():
        return GameEvent.DRAW

    if board.is_check():
        return GameEvent.CHECK

    # Was this a capture?  Note: board has already had the move pushed, so we
    # need to check via the move record rather than re-examining the board.
    is_capture = last_move.to_square in [
        sq for sq in chess.SQUARES if board.piece_at(sq) is not None
    ]
    # More reliable: use the move's captured piece flag indirectly via the
    # board's move stack.  The simplest check is whether a piece was on the
    # destination square before the move — we infer this from move metadata.
    # python-chess sets Move attributes; use board.is_capture on the *previous*
    # position.  Since the board is already pushed we can't call is_capture
    # directly, so we check the move's `promotion` flag and look at the piece
    # delta instead.  The safest approach: check if it's recorded as a capture
    # in the SAN (contains 'x').
    try:
        san = board.move_stack and board.san(last_move)
    except Exception:
        san = ""
    # Fallback: use the move object captured-piece hint stored in move.drop
    # (python-chess <0.30 doesn't have this). Use the SAN 'x' heuristic.
    is_capture_san = "x" in (san or "")

    # Eval swing: positive means White's position improved after the move.
    eval_swing = eval_after - eval_before

    # Determine eval improvement *for the mover*.
    # The mover was white if it's now black's turn (board.turn was flipped).
    mover_was_white = board.turn == chess.BLACK
    # Improvement from the mover's perspective:
    #   White moved → positive eval_swing is good for white (good for mover)
    #   Black moved → negative eval_swing is good for black (good for mover)
    mover_improvement = eval_swing if mover_was_white else -eval_swing

    # --- Player-specific events ---
    if is_player_move:
        # Sacrifice: player captured a piece of lower value than their capturer
        # OR moved a piece to an attacked square, but eval stayed stable.
        if is_capture_san:
            # Check piece values of capturer vs victim
            from sideboard.engine import PIECE_VALUES
            victim_sq = last_move.to_square
            capturer_sq = last_move.from_square
            # At this point the board has the move pushed, so the victim is gone
            # and the capturer piece is on victim_sq.
            capturer_piece = board.piece_at(victim_sq)
            # We need to figure out what the victim was — it's gone from the board.
            # Use the move's captured piece stored in the move stack's undo info.
            # python-chess stores this as board._stack entries; use peek at the
            # move stack.  The simplest way is to temporarily pop and check.
            try:
                board.pop()
                victim_piece = board.piece_at(victim_sq)
                board.push(last_move)
            except Exception:
                victim_piece = None

            if (
                capturer_piece is not None
                and victim_piece is not None
                and PIECE_VALUES.get(capturer_piece.piece_type, 0)
                    > PIECE_VALUES.get(victim_piece.piece_type, 0)
                and mover_improvement > -100  # eval didn't collapse
            ):
                return GameEvent.PLAYER_SACRIFICE

        # Great move: eval swung strongly in the player's favour and it wasn't
        # a trivial recapture.
        if mover_improvement > GREAT_MOVE_THRESHOLD and not is_capture_san:
            return GameEvent.PLAYER_GREAT_MOVE

        # Blunder: eval swung significantly against the player.
        if mover_improvement < -BLUNDER_THRESHOLD:
            return GameEvent.PLAYER_BLUNDER

    # --- Capture (non-sacrifice, non-player-great-move) ---
    if is_capture_san:
        return GameEvent.CAPTURE

    return None


def _game_info(difficulty: str, game_num: int, stats_summary: str) -> str:
    return f"Game {game_num} vs Chesster ({difficulty}) \u2502 {stats_summary}"


def run_game(
    difficulty: str = "club",
    player_color: str | None = None,
    resume: bool = False,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> None:
    """Run the main game loop."""
    console = Console()

    # Determine player color
    if player_color is None:
        import random
        player_color = random.choice(["white", "black"])

    player_is_white = player_color == "white"
    flipped = not player_is_white

    # Load or create game state
    if resume:
        saved = load_game(data_dir=data_dir)
        if saved:
            board = saved.to_board()
            difficulty = saved.difficulty
            player_color = saved.player_color
            player_is_white = player_color == "white"
            flipped = not player_is_white
        else:
            console.print("[yellow]No saved game found. Starting a new game.[/yellow]")
            board = chess.Board()
    else:
        # Check for existing game
        saved = load_game(data_dir=data_dir)
        if saved:
            console.print(
                f"[yellow]You have an unfinished game (move {len(saved.moves) // 2 + 1}, "
                f"{saved.difficulty}). Resume? [Y/n][/yellow]"
            )
            try:
                answer = input().strip().lower()
            except (EOFError, KeyboardInterrupt):
                return
            if answer != "n":
                board = saved.to_board()
                difficulty = saved.difficulty
                player_color = saved.player_color
                player_is_white = player_color == "white"
                flipped = not player_is_white
            else:
                delete_current_game(data_dir=data_dir)
                board = chess.Board()
        else:
            board = chess.Board()

    stats = load_stats(data_dir=data_dir)
    game_num = stats.games_played + 1
    chesster_msg = get_quip(GameEvent.GAME_START)
    last_move: chess.Move | None = board.move_stack[-1] if board.move_stack else None
    opening_announced = False

    # If player is black, let engine make the first move (if board is at start)
    if not player_is_white and not board.move_stack:
        engine_move = best_move(board, difficulty)
        board.push(engine_move)
        last_move = engine_move
        _save_state(board, difficulty, player_color, data_dir)

    # Main game loop
    while not board.is_game_over():
        move_list = format_move_list(board)
        info = _game_info(difficulty, game_num, stats.format_summary())

        render_screen(
            board, console,
            flipped=flipped,
            last_move=last_move,
            chesster_msg=chesster_msg,
            move_list=move_list,
            game_info=info,
        )

        # Is it the player's turn?
        player_turn = (board.turn == chess.WHITE) == player_is_white

        if not player_turn:
            # Engine's turn
            chesster_msg = get_quip(GameEvent.ENGINE_THINKING)
            eval_before = evaluate(board)
            engine_move = best_move(board, difficulty)
            board.push(engine_move)
            last_move = engine_move
            eval_after = evaluate(board)

            # Detect events (engine move — not a player move)
            event = detect_event(board, engine_move, eval_before=eval_before, eval_after=eval_after, is_player_move=False)

            # Check for opening
            if not opening_announced:
                opening = detect_opening(board)
                if opening:
                    chesster_msg = get_quip(GameEvent.OPENING_RECOGNIZED, name=opening)
                    opening_announced = True
                elif event == GameEvent.CAPTURE:
                    chesster_msg = get_quip(GameEvent.CAPTURE)
                elif event == GameEvent.CHECK:
                    chesster_msg = get_quip(GameEvent.CHECK)
                else:
                    chesster_msg = ""
            elif event:
                chesster_msg = get_quip(event)
            else:
                chesster_msg = ""

            _save_state(board, difficulty, player_color, data_dir)
            continue

        # Player's turn — get input
        try:
            user_input = input("Your move > ").strip()
        except (EOFError, KeyboardInterrupt):
            chesster_msg = get_quip(GameEvent.PLAYER_RESIGN)
            _end_game(board, "loss", difficulty, console, chesster_msg, data_dir, player_color)
            return

        if not user_input:
            continue

        result = parse_input(user_input, board)

        if result.kind == "command":
            if result.command == "quit":
                chesster_msg = get_quip(GameEvent.PLAYER_RESIGN)
                _end_game(board, "loss", difficulty, console, chesster_msg, data_dir, player_color)
                return

            elif result.command == "help":
                console.print("\n[bold]Commands:[/bold]")
                console.print("  [cyan]q/quit[/cyan]  — resign and exit")
                console.print("  [cyan]draw[/cyan]   — offer draw")
                console.print("  [cyan]undo[/cyan]   — take back last move pair")
                console.print("  [cyan]pgn[/cyan]    — show PGN so far")
                console.print("  [cyan]flip[/cyan]   — flip board orientation")
                console.print("  [cyan]help[/cyan]   — show this help")
                console.print("\n[dim]Moves: SAN notation (e4, Nf3, O-O, Bxe5, e8=Q)[/dim]")
                input("\nPress Enter to continue...")
                continue

            elif result.command == "pgn":
                pgn_str = export_pgn(board, result="*", difficulty=difficulty, player_color=player_color)
                console.print(f"\n[dim]{pgn_str}[/dim]")
                input("\nPress Enter to continue...")
                continue

            elif result.command == "flip":
                flipped = not flipped
                continue

            elif result.command == "undo":
                if len(board.move_stack) >= 2:
                    board.pop()  # engine's move
                    board.pop()  # player's move
                    last_move = board.move_stack[-1] if board.move_stack else None
                    chesster_msg = "Fine, take it back. I was winning anyway."
                    _save_state(board, difficulty, player_color, data_dir)
                else:
                    chesster_msg = "Nothing to undo. We just started!"
                continue

            elif result.command == "draw":
                current_eval = evaluate(board)
                # Convert eval to Chesster's (engine's) perspective.
                # If player is white, Chesster is black; positive eval means
                # white (player) is winning, so Chesster should decline.
                # We negate for black to get engine's perspective.
                chesster_eval = current_eval if not player_is_white else -current_eval
                # Accept draw if Chesster's perspective eval is within +-50cp
                if abs(chesster_eval) <= 50:
                    chesster_msg = get_quip(GameEvent.DRAW)
                    _end_game(board, "draw", difficulty, console, chesster_msg, data_dir, player_color)
                    return
                else:
                    chesster_msg = "Draw? In THIS position? Absolutely not."
                    continue

        elif result.kind == "error":
            console.print(f"\n[red]{result.message}[/red]")
            input("\nPress Enter to continue...")
            continue

        elif result.kind == "move" and result.move:
            eval_before = evaluate(board)
            board.push(result.move)
            last_move = result.move
            eval_after = evaluate(board)

            # Detect events for player's move
            event = detect_event(board, result.move, eval_before=eval_before, eval_after=eval_after, is_player_move=True)

            # Check for opening
            if not opening_announced:
                opening = detect_opening(board)
                if opening:
                    chesster_msg = get_quip(GameEvent.OPENING_RECOGNIZED, name=opening)
                    opening_announced = True
                elif event == GameEvent.PLAYER_BLUNDER:
                    chesster_msg = get_quip(GameEvent.PLAYER_BLUNDER)
                elif event == GameEvent.PLAYER_GREAT_MOVE:
                    chesster_msg = get_quip(GameEvent.PLAYER_GREAT_MOVE)
                elif event == GameEvent.PLAYER_SACRIFICE:
                    chesster_msg = get_quip(GameEvent.PLAYER_SACRIFICE)
                elif event == GameEvent.CAPTURE:
                    chesster_msg = get_quip(GameEvent.CAPTURE)
                else:
                    chesster_msg = ""
            elif event == GameEvent.PLAYER_BLUNDER:
                chesster_msg = get_quip(GameEvent.PLAYER_BLUNDER)
            elif event == GameEvent.PLAYER_GREAT_MOVE:
                chesster_msg = get_quip(GameEvent.PLAYER_GREAT_MOVE)
            elif event == GameEvent.PLAYER_SACRIFICE:
                chesster_msg = get_quip(GameEvent.PLAYER_SACRIFICE)
            elif event == GameEvent.CAPTURE:
                chesster_msg = get_quip(GameEvent.CAPTURE)
            elif event == GameEvent.CHECK:
                chesster_msg = get_quip(GameEvent.CHECK)
            else:
                chesster_msg = ""

            _save_state(board, difficulty, player_color, data_dir)

    # Game over
    if board.is_checkmate():
        winner = not board.turn  # side that delivered checkmate
        if (winner == chess.WHITE) == player_is_white:
            chesster_msg = get_quip(GameEvent.PLAYER_WINS)
            _end_game(board, "win", difficulty, console, chesster_msg, data_dir, player_color)
        else:
            move_num = len(board.move_stack)
            chesster_msg = get_quip(GameEvent.CHESSTER_WINS, move_number=move_num)
            _end_game(board, "loss", difficulty, console, chesster_msg, data_dir, player_color)
    else:
        chesster_msg = get_quip(GameEvent.DRAW)
        _end_game(board, "draw", difficulty, console, chesster_msg, data_dir, player_color)


def _save_state(
    board: chess.Board, difficulty: str, player_color: str, data_dir: Path,
) -> None:
    moves = [m.uci() for m in board.move_stack]
    state = GameState(
        fen=board.fen(),
        moves=moves,
        difficulty=difficulty,
        player_color=player_color,
    )
    save_game(state, data_dir=data_dir)


def _end_game(
    board: chess.Board,
    result: str,
    difficulty: str,
    console: Console,
    chesster_msg: str,
    data_dir: Path,
    player_color: str = "white",
) -> None:
    """Handle end-of-game: display, record, save PGN, clean up."""
    move_list = format_move_list(board)
    stats = load_stats(data_dir=data_dir)
    info = _game_info(difficulty, stats.games_played + 1, stats.format_summary())

    render_screen(
        board, console,
        flipped=False,
        last_move=board.move_stack[-1] if board.move_stack else None,
        chesster_msg=chesster_msg,
        move_list=move_list,
        game_info=info,
    )

    # Map result to PGN result string
    pgn_result = {"win": "1-0", "loss": "0-1", "draw": "1/2-1/2"}.get(result, "*")
    save_pgn(board, result=pgn_result, difficulty=difficulty, player_color=player_color, data_dir=data_dir)
    updated_stats = record_result(result, difficulty, data_dir=data_dir)
    delete_current_game(data_dir=data_dir)

    console.print(f"\n  [bold]Game saved.[/bold] {updated_stats.format_summary()}")
    console.print("  [dim]PGN saved to ~/.sideboard/games/[/dim]")
    console.print()
