"""Board rendering with Rich — the visual heart of Sideboard."""

from __future__ import annotations

import chess
from rich.console import Console
from rich.text import Text

# Use filled (solid) symbols for both colors — outlined pieces are too thin
# on colored terminal backgrounds. Colors differentiate the sides.
_PIECE_SYMBOLS: dict[tuple[int, bool], str] = {
    (chess.KING, chess.WHITE): "\u265a",
    (chess.QUEEN, chess.WHITE): "\u265b",
    (chess.ROOK, chess.WHITE): "\u265c",
    (chess.BISHOP, chess.WHITE): "\u265d",
    (chess.KNIGHT, chess.WHITE): "\u265e",
    (chess.PAWN, chess.WHITE): "\u265f",
    (chess.KING, chess.BLACK): "\u265a",
    (chess.QUEEN, chess.BLACK): "\u265b",
    (chess.ROOK, chess.BLACK): "\u265c",
    (chess.BISHOP, chess.BLACK): "\u265d",
    (chess.KNIGHT, chess.BLACK): "\u265e",
    (chess.PAWN, chess.BLACK): "\u265f",
}

_LIGHT_SQ = "#8fbc8f"
_DARK_SQ = "#4a7c59"
_HIGHLIGHT_LIGHT = "#c8a85c"
_HIGHLIGHT_DARK = "#a08030"

_PIECE_ORDER = {
    chess.QUEEN: 0, chess.ROOK: 1, chess.BISHOP: 2, chess.KNIGHT: 3, chess.PAWN: 4,
}


def piece_symbol(piece_type: int, color: bool) -> str:
    """Return the Unicode symbol for a chess piece."""
    return _PIECE_SYMBOLS[(piece_type, color)]


def captured_pieces(board: chess.Board) -> tuple[str, str]:
    """Return (white_captured, black_captured) as Unicode strings."""
    starting = {chess.PAWN: 8, chess.KNIGHT: 2, chess.BISHOP: 2,
                chess.ROOK: 2, chess.QUEEN: 1, chess.KING: 1}

    white_taken: list[tuple[int, str]] = []
    black_taken: list[tuple[int, str]] = []

    for piece_type in [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN]:
        white_remaining = len(board.pieces(piece_type, chess.WHITE))
        black_remaining = len(board.pieces(piece_type, chess.BLACK))
        white_missing = starting[piece_type] - white_remaining
        black_missing = starting[piece_type] - black_remaining

        for _ in range(max(0, black_missing)):
            white_taken.append((_PIECE_ORDER[piece_type],
                                piece_symbol(piece_type, chess.BLACK)))
        for _ in range(max(0, white_missing)):
            black_taken.append((_PIECE_ORDER[piece_type],
                                piece_symbol(piece_type, chess.WHITE)))

    white_taken.sort(key=lambda x: x[0])
    black_taken.sort(key=lambda x: x[0])

    return (
        " ".join(sym for _, sym in white_taken),
        " ".join(sym for _, sym in black_taken),
    )


_MATERIAL_VALUES = {
    chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
    chess.ROOK: 5, chess.QUEEN: 9,
}


def material_balance(board: chess.Board) -> int:
    """Return material balance from white's perspective. +3 means white is up a minor piece."""
    balance = 0
    for piece_type, value in _MATERIAL_VALUES.items():
        balance += len(board.pieces(piece_type, chess.WHITE)) * value
        balance -= len(board.pieces(piece_type, chess.BLACK)) * value
    return balance


def render_board(
    board: chess.Board,
    flipped: bool = False,
    last_move: chess.Move | None = None,
) -> str:
    """Render the board as a plain text string."""
    ranks = range(8) if flipped else range(7, -1, -1)
    files = range(7, -1, -1) if flipped else range(8)
    file_labels = [chess.FILE_NAMES[f] for f in files]

    lines: list[str] = []
    lines.append("    " + "   ".join(file_labels))
    lines.append("  \u250c" + "\u2500\u2500\u2500\u252c" * 7 + "\u2500\u2500\u2500\u2510")

    for i, rank in enumerate(ranks):
        rank_num = rank + 1
        row_parts: list[str] = []
        for file in files:
            square = chess.square(file, rank)
            piece = board.piece_at(square)
            if piece:
                sym = piece_symbol(piece.piece_type, piece.color)
                cell = f" {sym} "
            else:
                cell = "   "
            row_parts.append(cell)

        row = f"{rank_num} \u2502" + "\u2502".join(row_parts) + f"\u2502 {rank_num}"
        lines.append(row)

        if i < 7:
            lines.append("  \u251c" + "\u2500\u2500\u2500\u253c" * 7 + "\u2500\u2500\u2500\u2524")
        else:
            lines.append("  \u2514" + "\u2500\u2500\u2500\u2534" * 7 + "\u2500\u2500\u2500\u2518")

    lines.append("    " + "   ".join(file_labels))
    return "\n".join(lines)


def render_screen(
    board: chess.Board,
    console: Console,
    *,
    flipped: bool = False,
    last_move: chess.Move | None = None,
    chesster_msg: str = "",
    move_list: str = "",
    game_info: str = "",
) -> None:
    """Clear the terminal and render the full game screen."""
    console.clear()
    console.print()

    highlight_squares: set[int] = set()
    if last_move:
        highlight_squares = {last_move.from_square, last_move.to_square}

    ranks = range(8) if flipped else range(7, -1, -1)
    files = range(7, -1, -1) if flipped else range(8)
    file_labels = [chess.FILE_NAMES[f] for f in files]

    text = Text()
    text.append("    " + "   ".join(file_labels) + "\n", style="dim")
    text.append("  \u250c" + "\u2500\u2500\u2500\u252c" * 7 + "\u2500\u2500\u2500\u2510\n", style="dim green")

    for i, rank in enumerate(ranks):
        rank_num = rank + 1
        text.append(f"{rank_num} ", style="dim")
        text.append("\u2502", style="dim green")

        for j, file in enumerate(files):
            square = chess.square(file, rank)
            is_light = (rank + file) % 2 == 1
            is_highlighted = square in highlight_squares

            if is_highlighted:
                bg = _HIGHLIGHT_LIGHT if is_light else _HIGHLIGHT_DARK
            else:
                bg = _LIGHT_SQ if is_light else _DARK_SQ

            piece = board.piece_at(square)
            if piece:
                sym = piece_symbol(piece.piece_type, piece.color)
                fg = "#ffd700 bold" if piece.color == chess.WHITE else "#1a1a2e"
                text.append(f" {sym} ", style=f"{fg} on {bg}")
            else:
                text.append("   ", style=f"on {bg}")

            text.append("\u2502", style="dim green")

        text.append(f" {rank_num}\n", style="dim")

        if i < 7:
            text.append("  \u251c" + "\u2500\u2500\u2500\u253c" * 7 + "\u2500\u2500\u2500\u2524\n", style="dim green")
        else:
            text.append("  \u2514" + "\u2500\u2500\u2500\u2534" * 7 + "\u2500\u2500\u2500\u2518\n", style="dim green")

    text.append("    " + "   ".join(file_labels), style="dim")
    console.print(text)
    console.print()

    white_captured, black_captured = captured_pieces(board)
    bal = material_balance(board)
    cap_text = Text()
    cap_text.append("  White captured: ", style="dim")
    cap_text.append(white_captured or "\u2014", style="bold")
    cap_text.append("    Black captured: ", style="dim")
    cap_text.append(black_captured or "\u2014", style="bold")
    cap_text.append("    ")
    if bal > 0:
        cap_text.append(f"+{bal}", style="bold green")
        cap_text.append(" white", style="dim")
    elif bal < 0:
        cap_text.append(f"+{abs(bal)}", style="bold red")
        cap_text.append(" black", style="dim")
    else:
        cap_text.append("=", style="dim")
    console.print(cap_text)
    console.print()

    if move_list:
        ml_text = Text()
        ml_text.append("  ", style="dim")
        ml_text.append(move_list, style="bold")
        console.print(ml_text)
        console.print()

    if chesster_msg:
        ch_text = Text()
        ch_text.append("\u265f Chesster", style="bold magenta")
        ch_text.append(": ", style="magenta")
        ch_text.append(chesster_msg, style="italic")
        console.print(ch_text)
        console.print()

    if game_info:
        console.print(Text(f"  {game_info}", style="dim"))
        console.print()


def format_move_list(board: chess.Board) -> str:
    """Format the game's move list as compact SAN notation."""
    temp = board.copy()
    moves = list(board.move_stack)
    temp.reset()

    parts: list[str] = []
    for i, move in enumerate(moves):
        san = temp.san(move)
        if i % 2 == 0:
            move_num = i // 2 + 1
            parts.append(f"{move_num}.{san}")
        else:
            parts.append(san)
        temp.push(move)

    return "  ".join(parts)
