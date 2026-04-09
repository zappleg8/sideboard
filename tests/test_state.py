import json
from pathlib import Path

import chess

from sideboard.state import (
    GameState,
    Stats,
    save_game,
    load_game,
    delete_current_game,
    load_stats,
    record_result,
    save_pgn,
    export_pgn,
)


def test_game_state_to_dict(tmp_path):
    gs = GameState(fen=chess.STARTING_FEN, moves=[], difficulty="club", player_color="white")
    d = gs.to_dict()
    assert d["fen"] == chess.STARTING_FEN
    assert d["difficulty"] == "club"
    assert "started_at" in d


def test_game_state_from_dict():
    d = {"fen": chess.STARTING_FEN, "moves": ["e2e4", "e7e5"], "difficulty": "casual", "player_color": "black", "started_at": "2026-04-08T14:00:00Z"}
    gs = GameState.from_dict(d)
    assert gs.difficulty == "casual"
    assert len(gs.moves) == 2


def test_save_and_load_game(tmp_path):
    gs = GameState(fen=chess.STARTING_FEN, moves=["e2e4"], difficulty="club", player_color="white")
    save_game(gs, data_dir=tmp_path)
    loaded = load_game(data_dir=tmp_path)
    assert loaded is not None
    assert loaded.fen == gs.fen
    assert loaded.moves == gs.moves


def test_load_game_returns_none_when_no_game(tmp_path):
    assert load_game(data_dir=tmp_path) is None


def test_delete_current_game(tmp_path):
    gs = GameState(fen=chess.STARTING_FEN, moves=[], difficulty="club", player_color="white")
    save_game(gs, data_dir=tmp_path)
    delete_current_game(data_dir=tmp_path)
    assert load_game(data_dir=tmp_path) is None


def test_load_stats_empty(tmp_path):
    stats = load_stats(data_dir=tmp_path)
    assert stats.total_wins == 0
    assert stats.total_losses == 0
    assert stats.games_played == 0


def test_record_result(tmp_path):
    record_result("win", "club", data_dir=tmp_path)
    record_result("loss", "club", data_dir=tmp_path)
    record_result("win", "casual", data_dir=tmp_path)
    stats = load_stats(data_dir=tmp_path)
    assert stats.total_wins == 2
    assert stats.total_losses == 1
    assert stats.games_played == 3
    assert stats.by_difficulty["club"]["wins"] == 1
    assert stats.by_difficulty["club"]["losses"] == 1
    assert stats.by_difficulty["casual"]["wins"] == 1


def test_save_pgn(tmp_path):
    board = chess.Board()
    board.push_san("e4")
    board.push_san("e5")
    save_pgn(board, result="*", difficulty="club", data_dir=tmp_path)
    games_dir = tmp_path / "games"
    pgn_files = list(games_dir.glob("*.pgn"))
    assert len(pgn_files) == 1
    content = pgn_files[0].read_text()
    assert "Chesster" in content
    assert "1. e4 e5" in content


def test_export_pgn():
    board = chess.Board()
    board.push_san("e4")
    board.push_san("e5")
    board.push_san("Nf3")
    pgn_str = export_pgn(board, result="*", difficulty="casual")
    assert "1. e4 e5 2. Nf3" in pgn_str
    assert "Chesster" in pgn_str
