"""Game state persistence — saves to ~/.sideboard/."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import chess
import chess.pgn

DEFAULT_DATA_DIR = Path.home() / ".sideboard"


@dataclass
class GameState:
    fen: str
    moves: list[str]
    difficulty: str
    player_color: str
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {"fen": self.fen, "moves": self.moves, "difficulty": self.difficulty, "player_color": self.player_color, "started_at": self.started_at}

    @classmethod
    def from_dict(cls, d: dict) -> GameState:
        return cls(fen=d["fen"], moves=d["moves"], difficulty=d["difficulty"], player_color=d["player_color"], started_at=d.get("started_at", ""))

    def to_board(self) -> chess.Board:
        board = chess.Board()
        for uci in self.moves:
            board.push_uci(uci)
        return board


@dataclass
class Stats:
    total_wins: int = 0
    total_losses: int = 0
    total_draws: int = 0
    games_played: int = 0
    by_difficulty: dict[str, dict[str, int]] = field(default_factory=dict)
    last_played: str = ""

    def to_dict(self) -> dict:
        return {"total": {"wins": self.total_wins, "losses": self.total_losses, "draws": self.total_draws}, "by_difficulty": self.by_difficulty, "games_played": self.games_played, "last_played": self.last_played}

    @classmethod
    def from_dict(cls, d: dict) -> Stats:
        total = d.get("total", {})
        return cls(total_wins=total.get("wins", 0), total_losses=total.get("losses", 0), total_draws=total.get("draws", 0), games_played=d.get("games_played", 0), by_difficulty=d.get("by_difficulty", {}), last_played=d.get("last_played", ""))

    def format_summary(self) -> str:
        return f"W:{self.total_wins} L:{self.total_losses} D:{self.total_draws}"


def _ensure_dir(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)


def save_game(state: GameState, *, data_dir: Path = DEFAULT_DATA_DIR) -> None:
    _ensure_dir(data_dir)
    (data_dir / "current_game.json").write_text(json.dumps(state.to_dict(), indent=2))


def load_game(*, data_dir: Path = DEFAULT_DATA_DIR) -> GameState | None:
    path = data_dir / "current_game.json"
    if not path.exists():
        return None
    try:
        return GameState.from_dict(json.loads(path.read_text()))
    except (json.JSONDecodeError, KeyError):
        return None


def delete_current_game(*, data_dir: Path = DEFAULT_DATA_DIR) -> None:
    path = data_dir / "current_game.json"
    if path.exists():
        path.unlink()


def load_stats(*, data_dir: Path = DEFAULT_DATA_DIR) -> Stats:
    path = data_dir / "stats.json"
    if not path.exists():
        return Stats()
    try:
        return Stats.from_dict(json.loads(path.read_text()))
    except (json.JSONDecodeError, KeyError):
        return Stats()


def record_result(result: str, difficulty: str, *, data_dir: Path = DEFAULT_DATA_DIR) -> Stats:
    _ensure_dir(data_dir)
    stats = load_stats(data_dir=data_dir)
    if result == "win":
        stats.total_wins += 1
    elif result == "loss":
        stats.total_losses += 1
    elif result == "draw":
        stats.total_draws += 1
    stats.games_played += 1
    stats.last_played = datetime.now(timezone.utc).isoformat()
    if difficulty not in stats.by_difficulty:
        stats.by_difficulty[difficulty] = {"wins": 0, "losses": 0, "draws": 0}
    diff_stats = stats.by_difficulty[difficulty]
    if result == "win":
        diff_stats["wins"] += 1
    elif result == "loss":
        diff_stats["losses"] += 1
    elif result == "draw":
        diff_stats["draws"] += 1
    (data_dir / "stats.json").write_text(json.dumps(stats.to_dict(), indent=2))
    return stats


def export_pgn(board: chess.Board, result: str = "*", difficulty: str = "club") -> str:
    game = chess.pgn.Game()
    game.headers["Event"] = "Sideboard Game"
    game.headers["Site"] = "Terminal"
    game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
    game.headers["White"] = "Player"
    game.headers["Black"] = "Chesster"
    game.headers["Result"] = result
    game.headers["Annotator"] = f"Sideboard v0.1.0 ({difficulty})"
    node = game
    temp = chess.Board()
    for move in board.move_stack:
        node = node.add_variation(move)
        temp.push(move)
    return str(game)


def save_pgn(board: chess.Board, result: str = "*", difficulty: str = "club", *, data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    _ensure_dir(data_dir / "games")
    pgn_str = export_pgn(board, result=result, difficulty=difficulty)
    date_str = datetime.now().strftime("%Y-%m-%d")
    games_dir = data_dir / "games"
    existing = list(games_dir.glob(f"{date_str}_*.pgn"))
    num = len(existing) + 1
    filename = f"{date_str}_{num:03d}.pgn"
    path = games_dir / filename
    path.write_text(pgn_str)
    return path
