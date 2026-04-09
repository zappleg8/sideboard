"""Minimax chess engine with alpha-beta pruning — Chesster's brain."""

from __future__ import annotations

import random

import chess

PIECE_VALUES: dict[int, int] = {
    chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
    chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000,
}

CHECKMATE_SCORE = 100000
DRAW_SCORE = 0

DIFFICULTY_DEPTH: dict[str, int] = {"casual": 2, "club": 3, "shark": 4}

_PAWN_TABLE = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]

_KNIGHT_TABLE = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
]

_BISHOP_TABLE = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
]

_ROOK_TABLE = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
]

_QUEEN_TABLE = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20,
]

_KING_MIDDLEGAME_TABLE = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20,
]

_KING_ENDGAME_TABLE = [
    -50,-40,-30,-20,-20,-30,-40,-50,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50,
]

_PST_MIDDLEGAME: dict[int, list[int]] = {
    chess.PAWN: _PAWN_TABLE, chess.KNIGHT: _KNIGHT_TABLE,
    chess.BISHOP: _BISHOP_TABLE, chess.ROOK: _ROOK_TABLE,
    chess.QUEEN: _QUEEN_TABLE, chess.KING: _KING_MIDDLEGAME_TABLE,
}

_PST_ENDGAME: dict[int, list[int]] = {
    chess.PAWN: _PAWN_TABLE, chess.KNIGHT: _KNIGHT_TABLE,
    chess.BISHOP: _BISHOP_TABLE, chess.ROOK: _ROOK_TABLE,
    chess.QUEEN: _QUEEN_TABLE, chess.KING: _KING_ENDGAME_TABLE,
}

_ENDGAME_THRESHOLD = 1300


def _is_endgame(board: chess.Board) -> bool:
    material = 0
    for piece_type in [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]:
        material += len(board.pieces(piece_type, chess.WHITE)) * PIECE_VALUES[piece_type]
        material += len(board.pieces(piece_type, chess.BLACK)) * PIECE_VALUES[piece_type]
    return material <= _ENDGAME_THRESHOLD


def _pst_value(piece_type: int, square: int, color: bool, endgame: bool) -> int:
    table = (_PST_ENDGAME if endgame else _PST_MIDDLEGAME)[piece_type]
    if color == chess.WHITE:
        return table[square]
    else:
        mirrored = chess.square(chess.square_file(square), 7 - chess.square_rank(square))
        return table[mirrored]


def evaluate(board: chess.Board) -> int:
    """Evaluate board position. Positive = white advantage. Returns centipawns."""
    if board.is_checkmate():
        return -CHECKMATE_SCORE if board.turn == chess.WHITE else CHECKMATE_SCORE
    if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
        return DRAW_SCORE

    endgame = _is_endgame(board)
    score = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue
        value = PIECE_VALUES[piece.piece_type]
        pst = _pst_value(piece.piece_type, square, piece.color, endgame)
        if piece.color == chess.WHITE:
            score += value + pst
        else:
            score -= value + pst
    return score


def _mvv_lva_score(board: chess.Board, move: chess.Move) -> int:
    if not board.is_capture(move):
        return 0
    victim = board.piece_at(move.to_square)
    attacker = board.piece_at(move.from_square)
    if victim and attacker:
        return PIECE_VALUES.get(victim.piece_type, 0) * 10 - PIECE_VALUES.get(attacker.piece_type, 0)
    return 0


def _order_moves(board: chess.Board) -> list[chess.Move]:
    moves = list(board.legal_moves)
    scored: list[tuple[int, chess.Move]] = []
    for move in moves:
        score = 0
        if board.is_capture(move):
            score = 10000 + _mvv_lva_score(board, move)
        elif board.gives_check(move):
            score = 5000
        scored.append((score, move))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored]


def _eval_for_current_player(board: chess.Board) -> int:
    """Return evaluate() from the current player's perspective (for negamax)."""
    raw = evaluate(board)
    return raw if board.turn == chess.WHITE else -raw


def _quiescence(board: chess.Board, alpha: int, beta: int) -> int:
    stand_pat = _eval_for_current_player(board)
    if stand_pat >= beta:
        return beta
    if stand_pat > alpha:
        alpha = stand_pat
    for move in _order_moves(board):
        if not board.is_capture(move):
            continue
        board.push(move)
        score = -_quiescence(board, -beta, -alpha)
        board.pop()
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha


def _alphabeta(board: chess.Board, depth: int, alpha: int, beta: int, use_quiescence: bool) -> int:
    if depth == 0:
        if use_quiescence:
            return _quiescence(board, alpha, beta)
        return _eval_for_current_player(board)
    if board.is_game_over():
        return _eval_for_current_player(board)
    for move in _order_moves(board):
        board.push(move)
        score = -_alphabeta(board, depth - 1, -beta, -alpha, use_quiescence)
        board.pop()
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha


def top_moves(board: chess.Board, n: int = 3, depth: int = 4) -> list[tuple[chess.Move, float]]:
    """Return top N moves with evaluations (positive = good for side to move)."""
    use_quiescence = depth >= 4
    move_scores: list[tuple[chess.Move, int]] = []
    for move in _order_moves(board):
        board.push(move)
        score = -_alphabeta(board, depth - 1, -CHECKMATE_SCORE, CHECKMATE_SCORE, use_quiescence)
        board.pop()
        move_scores.append((move, score))
    move_scores.sort(key=lambda x: x[1], reverse=True)
    return [(m, s / 100.0) for m, s in move_scores[:n]]


def best_move(board: chess.Board, difficulty: str) -> chess.Move:
    """Return engine's chosen move for the given difficulty."""
    depth = DIFFICULTY_DEPTH.get(difficulty, 3)
    use_quiescence = difficulty == "shark"
    move_scores: list[tuple[chess.Move, int]] = []
    for move in _order_moves(board):
        board.push(move)
        score = -_alphabeta(board, depth - 1, -CHECKMATE_SCORE, CHECKMATE_SCORE, use_quiescence)
        board.pop()
        move_scores.append((move, score))
    move_scores.sort(key=lambda x: x[1], reverse=True)
    if not move_scores:
        raise ValueError("No legal moves available")
    if difficulty == "casual" and len(move_scores) >= 2 and random.random() < 0.2:
        candidates = move_scores[:min(3, len(move_scores))]
        return random.choice(candidates)[0]
    return move_scores[0][0]
