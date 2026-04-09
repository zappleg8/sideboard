import chess
from sideboard.board import render_board, piece_symbol, captured_pieces


def test_piece_symbol_white_king():
    assert piece_symbol(chess.KING, chess.WHITE) == "\u2654"


def test_piece_symbol_black_pawn():
    assert piece_symbol(chess.PAWN, chess.BLACK) == "\u265f"


def test_render_board_starting_position():
    board = chess.Board()
    output = render_board(board)
    assert "a   b   c   d   e   f   g   h" in output
    assert "8 \u2502" in output
    assert "1 \u2502" in output
    assert "\u265c" in output  # black rook (filled)
    assert "\u2656" in output  # white rook (outlined)


def test_render_board_flipped():
    board = chess.Board()
    output = render_board(board, flipped=True)
    first_rank_pos = output.index("1 \u2502")
    eighth_rank_pos = output.index("8 \u2502")
    assert first_rank_pos < eighth_rank_pos


def test_render_board_highlights_last_move():
    board = chess.Board()
    move = chess.Move.from_uci("e2e4")
    board.push(move)
    output = render_board(board, last_move=move)
    assert "\u2654" in output or "\u265a" in output


def test_captured_pieces_initial():
    board = chess.Board()
    white_captured, black_captured = captured_pieces(board)
    assert white_captured == ""
    assert black_captured == ""


def test_captured_pieces_after_capture():
    board = chess.Board()
    board.push_san("e4")
    board.push_san("d5")
    board.push_san("exd5")
    white_captured, black_captured = captured_pieces(board)
    assert "\u265f" in white_captured
    assert black_captured == ""
