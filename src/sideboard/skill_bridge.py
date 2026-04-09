"""Subagent bridge — JSON CLI interface for Claude playing as Chesster."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import chess

from sideboard.board import render_board
from sideboard.chesster import GameEvent, get_quip
from sideboard.engine import evaluate, top_moves
from sideboard.game import detect_event, detect_opening
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


def _save_state(
    board: chess.Board,
    difficulty: str,
    player_color: str,
    data_dir: Path,
) -> None:
    moves = [m.uci() for m in board.move_stack]
    state = GameState(
        fen=board.fen(),
        moves=moves,
        difficulty=difficulty,
        player_color=player_color,
    )
    save_game(state, data_dir=data_dir)


def _parse_move(san: str, board: chess.Board) -> chess.Move | None:
    """Try to parse a move as SAN, then UCI fallback. Returns None if invalid."""
    try:
        return board.parse_san(san)
    except (chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError):
        pass
    try:
        move = board.parse_uci(san)
        if move in board.legal_moves:
            return move
    except (chess.InvalidMoveError, ValueError):
        pass
    return None


def _detect_game_over(board: chess.Board) -> dict[str, Any]:
    """Return game_over info dict."""
    if not board.is_game_over():
        return {"game_over": False}

    if board.is_checkmate():
        winner = "black" if board.turn == chess.WHITE else "white"
        return {"game_over": True, "reason": "checkmate", "winner": winner}
    if board.is_stalemate():
        return {"game_over": True, "reason": "stalemate"}
    if board.is_insufficient_material():
        return {"game_over": True, "reason": "insufficient_material"}
    if board.is_seventyfive_moves():
        return {"game_over": True, "reason": "seventy_five_moves"}
    if board.is_fivefold_repetition():
        return {"game_over": True, "reason": "fivefold_repetition"}
    return {"game_over": True, "reason": "draw"}


def bridge_new(difficulty: str, color: str, *, data_dir: Path = DEFAULT_DATA_DIR) -> str:
    """Create a new game and return JSON with fen, board_render, game_id."""
    data_dir.mkdir(parents=True, exist_ok=True)

    board = chess.Board()
    game_id = str(uuid.uuid4())

    # Store game_id in a sidecar file
    (data_dir / "current_game_id.txt").write_text(game_id)

    _save_state(board, difficulty, color, data_dir)

    player_is_white = color == "white"
    flipped = not player_is_white

    result: dict[str, Any] = {
        "game_id": game_id,
        "fen": board.fen(),
        "board_render": render_board(board, flipped=flipped),
        "difficulty": difficulty,
        "player_color": color,
        "turn": "white",
        "move_number": 1,
        "chesster_msg": get_quip(GameEvent.GAME_START),
    }
    return json.dumps(result)


def bridge_move(san: str, *, data_dir: Path = DEFAULT_DATA_DIR) -> str:
    """Two-phase protocol step 1: apply player's move and return engine suggestions."""
    state = load_game(data_dir=data_dir)
    if state is None:
        return json.dumps({"error": "No active game. Call bridge_new first.", "valid": False})

    board = state.to_board()

    # Validate the move
    move = _parse_move(san, board)
    if move is None:
        legal_moves = [board.san(m) for m in board.legal_moves]
        return json.dumps({
            "valid": False,
            "error": f"Illegal or invalid move: '{san}'",
            "legal_moves": sorted(legal_moves),
        })

    # Apply player's move
    eval_before = evaluate(board)
    board.push(move)
    eval_after = evaluate(board)

    # Detect event for player's move
    event = detect_event(board, move, eval_before=eval_before, eval_after=eval_after, is_player_move=True)
    opening = detect_opening(board)

    event_name: str | None = None
    event_data: dict[str, Any] = {}
    if opening:
        event_name = GameEvent.OPENING_RECOGNIZED.value
        event_data = {"name": opening}
    elif event is not None:
        event_name = event.value

    # Get engine suggestions (board is now at the position after player's move)
    game_over_info = _detect_game_over(board)
    suggestions: list[tuple[str, float]] = []
    if not game_over_info["game_over"]:
        raw_suggestions = top_moves(board, n=3, depth=2)
        for eng_move, score in raw_suggestions:
            suggestions.append((board.san(eng_move), round(score, 2)))

    # Save state with player's move applied (NOT engine's)
    _save_state(board, state.difficulty, state.player_color, data_dir)

    player_is_white = state.player_color == "white"
    flipped = not player_is_white

    result: dict[str, Any] = {
        "valid": True,
        "fen": board.fen(),
        "board_render": render_board(board, flipped=flipped, last_move=move),
        "engine_suggestions": suggestions,
        "event": event_name,
        "event_data": event_data,
        **game_over_info,
    }
    return json.dumps(result)


def bridge_respond(san: str, *, data_dir: Path = DEFAULT_DATA_DIR) -> str:
    """Two-phase protocol step 2: apply the chosen engine move."""
    state = load_game(data_dir=data_dir)
    if state is None:
        return json.dumps({"error": "No active game. Call bridge_new first."})

    board = state.to_board()

    move = _parse_move(san, board)
    if move is None:
        legal_moves = [board.san(m) for m in board.legal_moves]
        return json.dumps({
            "error": f"Invalid engine move: '{san}'",
            "legal_moves": sorted(legal_moves),
        })

    eval_before = evaluate(board)
    board.push(move)
    eval_after = evaluate(board)

    event = detect_event(board, move, eval_before=eval_before, eval_after=eval_after, is_player_move=False)
    opening = detect_opening(board)

    event_name: str | None = None
    event_data: dict[str, Any] = {}
    if opening:
        event_name = GameEvent.OPENING_RECOGNIZED.value
        event_data = {"name": opening}
    elif event is not None:
        event_name = event.value

    game_over_info = _detect_game_over(board)

    _save_state(board, state.difficulty, state.player_color, data_dir)

    player_is_white = state.player_color == "white"
    flipped = not player_is_white

    result: dict[str, Any] = {
        "fen": board.fen(),
        "board_render": render_board(board, flipped=flipped, last_move=move),
        "event": event_name,
        "event_data": event_data,
        "move_number": board.fullmove_number,
        **game_over_info,
    }
    return json.dumps(result)


def bridge_state(*, data_dir: Path = DEFAULT_DATA_DIR) -> str:
    """Return current game state as JSON."""
    state = load_game(data_dir=data_dir)
    if state is None:
        return json.dumps({"error": "No active game."})

    board = state.to_board()
    player_is_white = state.player_color == "white"
    flipped = not player_is_white
    last_move = board.move_stack[-1] if board.move_stack else None

    result: dict[str, Any] = {
        "fen": board.fen(),
        "board_render": render_board(board, flipped=flipped, last_move=last_move),
        "move_number": board.fullmove_number,
        "difficulty": state.difficulty,
        "player_color": state.player_color,
        "turn": "white" if board.turn == chess.WHITE else "black",
        "moves": state.moves,
        "started_at": state.started_at,
    }
    return json.dumps(result)


def bridge_resign(*, data_dir: Path = DEFAULT_DATA_DIR) -> str:
    """Resign the current game, record loss, and return stats."""
    state = load_game(data_dir=data_dir)
    if state is None:
        return json.dumps({"error": "No active game."})

    board = state.to_board()
    pgn_result = "0-1" if state.player_color == "white" else "1-0"
    pgn_str = export_pgn(board, result=pgn_result, difficulty=state.difficulty, player_color=state.player_color)
    save_pgn(board, result=pgn_result, difficulty=state.difficulty, player_color=state.player_color, data_dir=data_dir)
    updated_stats = record_result("loss", state.difficulty, data_dir=data_dir)
    delete_current_game(data_dir=data_dir)

    result: dict[str, Any] = {
        "result": "loss",
        "pgn": pgn_str,
        "stats": updated_stats.to_dict(),
        "chesster_msg": get_quip(GameEvent.PLAYER_RESIGN),
    }
    return json.dumps(result)


def handle_bridge(args: "argparse.Namespace") -> str:  # noqa: F821
    """Dispatch argparse Namespace to the appropriate bridge function.

    Reads args.bridge_command, args.move_arg, args.bridge_difficulty,
    args.bridge_color (and the global args.difficulty / args.color as
    fallbacks).
    """
    import argparse  # local import to avoid circular-import risk

    cmd = (args.bridge_command or "state").lower()

    # Resolve difficulty and color with fallbacks
    difficulty = args.bridge_difficulty or getattr(args, "difficulty", "club") or "club"
    color = args.bridge_color or getattr(args, "color", None) or "white"

    if cmd == "new":
        result = bridge_new(difficulty, color)
        print(result)
        return result

    elif cmd == "move":
        move_san = args.move_arg
        if not move_san:
            result = json.dumps({"error": "Usage: bridge move <san>"})
            print(result)
            return result
        result = bridge_move(move_san)
        print(result)
        return result

    elif cmd == "respond":
        move_san = args.move_arg
        if not move_san:
            result = json.dumps({"error": "Usage: bridge respond <san>"})
            print(result)
            return result
        result = bridge_respond(move_san)
        print(result)
        return result

    elif cmd == "state":
        result = bridge_state()
        print(result)
        return result

    elif cmd == "resign":
        result = bridge_resign()
        print(result)
        return result

    else:
        result = json.dumps({"error": f"Unknown bridge command: '{cmd}'"})
        print(result)
        return result
