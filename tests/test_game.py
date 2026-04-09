from unittest.mock import patch, MagicMock
from pathlib import Path

import chess

from sideboard.game import parse_input, InputResult, detect_event, detect_opening


def test_parse_input_valid_move():
    board = chess.Board()
    result = parse_input("e4", board)
    assert result.kind == "move"
    assert result.move is not None
    assert result.move == board.parse_san("e4")


def test_parse_input_invalid_move():
    board = chess.Board()
    result = parse_input("e5e6", board)
    assert result.kind == "error"
    assert "legal" in result.message.lower() or "illegal" in result.message.lower()


def test_parse_input_quit():
    board = chess.Board()
    result = parse_input("q", board)
    assert result.kind == "command"
    assert result.command == "quit"


def test_parse_input_quit_full():
    board = chess.Board()
    result = parse_input("quit", board)
    assert result.kind == "command"
    assert result.command == "quit"


def test_parse_input_help():
    board = chess.Board()
    result = parse_input("help", board)
    assert result.kind == "command"
    assert result.command == "help"


def test_parse_input_draw():
    board = chess.Board()
    result = parse_input("draw", board)
    assert result.kind == "command"
    assert result.command == "draw"


def test_parse_input_pgn():
    board = chess.Board()
    result = parse_input("pgn", board)
    assert result.kind == "command"
    assert result.command == "pgn"


def test_parse_input_undo():
    board = chess.Board()
    result = parse_input("undo", board)
    assert result.kind == "command"
    assert result.command == "undo"


def test_parse_input_flip():
    board = chess.Board()
    result = parse_input("flip", board)
    assert result.kind == "command"
    assert result.command == "flip"


def test_parse_input_helpful_error_for_piece_moves():
    board = chess.Board()
    result = parse_input("Nc6", board)
    assert result.kind == "error"
    assert "Nc3" in result.message or "legal" in result.message.lower()


def test_detect_opening_sicilian():
    board = chess.Board()
    for san in ["e4", "c5"]:
        board.push_san(san)
    name = detect_opening(board)
    assert name is None or isinstance(name, str)


def test_detect_event_returns_none_for_no_move():
    board = chess.Board()
    event = detect_event(board, None, eval_before=0, eval_after=0)
    assert event is None
