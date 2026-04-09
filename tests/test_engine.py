import chess
from sideboard.engine import evaluate, best_move, top_moves


def test_evaluate_starting_position():
    board = chess.Board()
    score = evaluate(board)
    assert -50 < score < 50


def test_evaluate_white_up_queen():
    board = chess.Board()
    board.remove_piece_at(chess.D8)
    score = evaluate(board)
    assert score > 800


def test_evaluate_material_advantage():
    board = chess.Board()
    board.remove_piece_at(chess.D8)
    board.remove_piece_at(chess.A8)
    score = evaluate(board)
    assert score > 1300


def test_best_move_returns_legal_move():
    board = chess.Board()
    move = best_move(board, "casual")
    assert move in board.legal_moves


def test_best_move_finds_mate_in_one():
    board = chess.Board("k7/8/1K6/8/8/8/8/R7 w - - 0 1")
    move = best_move(board, "club")
    board.push(move)
    assert board.is_checkmate()


def test_best_move_casual_returns_move():
    board = chess.Board()
    move = best_move(board, "casual")
    assert move is not None
    assert move in board.legal_moves


def test_best_move_shark_returns_move():
    board = chess.Board()
    move = best_move(board, "shark")
    assert move is not None
    assert move in board.legal_moves


def test_top_moves_returns_sorted():
    board = chess.Board()
    moves = top_moves(board, n=3, depth=2)
    assert len(moves) <= 3
    assert all(isinstance(m, tuple) and len(m) == 2 for m in moves)
    evals = [ev for _, ev in moves]
    assert evals == sorted(evals, reverse=True)


def test_top_moves_all_legal():
    board = chess.Board()
    moves = top_moves(board, n=5, depth=2)
    for move, _ in moves:
        assert move in board.legal_moves
