import json
from pathlib import Path

from sideboard.skill_bridge import bridge_new, bridge_move, bridge_respond, bridge_state, bridge_resign


def test_bridge_new(tmp_path):
    result = bridge_new("club", "white", data_dir=tmp_path)
    data = json.loads(result)
    assert "fen" in data
    assert "board_render" in data
    assert "game_id" in data


def test_bridge_move_valid(tmp_path):
    bridge_new("club", "white", data_dir=tmp_path)
    result = bridge_move("e4", data_dir=tmp_path)
    data = json.loads(result)
    assert data["valid"] is True
    assert "engine_suggestions" in data
    assert len(data["engine_suggestions"]) >= 1


def test_bridge_move_invalid(tmp_path):
    bridge_new("club", "white", data_dir=tmp_path)
    result = bridge_move("Qh7", data_dir=tmp_path)
    data = json.loads(result)
    assert data["valid"] is False
    assert "legal_moves" in data


def test_bridge_respond(tmp_path):
    bridge_new("club", "white", data_dir=tmp_path)
    move_result = json.loads(bridge_move("e4", data_dir=tmp_path))
    assert move_result["valid"]
    suggestion = move_result["engine_suggestions"][0][0]
    respond_result = json.loads(bridge_respond(suggestion, data_dir=tmp_path))
    assert "fen" in respond_result
    assert "board_render" in respond_result


def test_bridge_state(tmp_path):
    bridge_new("club", "white", data_dir=tmp_path)
    result = bridge_state(data_dir=tmp_path)
    data = json.loads(result)
    assert "fen" in data
    assert "move_number" in data


def test_bridge_resign(tmp_path):
    bridge_new("club", "white", data_dir=tmp_path)
    result = bridge_resign(data_dir=tmp_path)
    data = json.loads(result)
    assert "result" in data
    assert "pgn" in data
    assert "stats" in data
