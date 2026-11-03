"""Super Rotation System (SRS) rotation and wall-kick implementation."""
from typing import Dict, Tuple
from .board import Board, Piece

# Offsets are expressed in screen coordinates: +x right, +y down.
# These are the standard SRS transition tests, ordered by preference.
JLSTZ_KICKS: Dict[Tuple[int, int], Tuple[Tuple[int, int], ...]] = {
    (0, 1): ((0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)),
    (1, 0): ((0, 0), (1, 0), (1, 1), (0, -2), (1, -2)),
    (1, 2): ((0, 0), (1, 0), (1, 1), (0, -2), (1, -2)),
    (2, 1): ((0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)),
    (2, 3): ((0, 0), (1, 0), (1, -1), (0, 2), (1, 2)),
    (3, 2): ((0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)),
    (3, 0): ((0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)),
    (0, 3): ((0, 0), (1, 0), (1, -1), (0, 2), (1, 2)),
}

I_KICKS: Dict[Tuple[int, int], Tuple[Tuple[int, int], ...]] = {
    (0, 1): ((0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)),
    (1, 0): ((0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)),
    (1, 2): ((0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)),
    (2, 1): ((0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)),
    (2, 3): ((0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)),
    (3, 2): ((0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)),
    (3, 0): ((0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)),
    (0, 3): ((0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)),
}


def try_rotate(board: Board, piece: Piece, direction: int = 1):
    """Try rotating clockwise (+1) or counter-clockwise (-1).

    Returns (success, kick_index). kick_index is 0 for the basic rotation,
    1..4 for wall-kick tests, and None on failure.
    The input Piece is not mutated.
    """
    if direction not in (-1, 1):
        raise ValueError("direction must be +1 (CW) or -1 (CCW)")
    old = piece.rotation % 4
    new = (old + direction) % 4
    table = I_KICKS if piece.kind == "I" else JLSTZ_KICKS
    tests = table[(old, new)]

    for index, (dx, dy) in enumerate(tests):
        candidate = piece.clone()
        candidate.rotation = new
        candidate.x += dx
        candidate.y += dy
        if board.is_valid(candidate):
            piece.x = candidate.x
            piece.y = candidate.y
            piece.rotation = candidate.rotation
            return True, index
    return False, None
