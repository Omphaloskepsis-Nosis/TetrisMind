import time
from typing import List, Tuple, Optional
from ai.features import evaluate_state

PIECES = {
    1: [[1, 1, 1, 1]], 2: [[1, 1], [1, 1]], 3: [[0, 1, 0], [1, 1, 1]],
    4: [[0, 0, 1], [1, 1, 1]], 5: [[1, 0, 0], [1, 1, 1]],
    6: [[0, 1, 1], [1, 1, 0]], 7: [[1, 1, 0], [0, 1, 1]]
}


def rotate_piece(piece: List[List[int]]) -> List[List[int]]:
    return [list(row) for row in zip(*piece[::-1])]


def get_all_rotations(piece_type: int) -> List[List[List[int]]]:
    if piece_type not in PIECES:
        return [PIECES[1]]
    base = PIECES[piece_type]
    rotations = [base]
    for _ in range(3):
        base = rotate_piece(base)
        if base not in rotations:
            rotations.append(base)
    return rotations


def simulate_drop(board: List[List[int]], piece: List[List[int]], start_col: int) -> Tuple[
    Optional[List[List[int]]], int]:
    new_board = [row[:] for row in board]
    rows, cols = len(board), len(board[0])
    piece_rows, piece_cols = len(piece), len(piece[0])

    if start_col < 0 or start_col + piece_cols > cols:
        return None, 0

    drop_row = 0
    for r in range(rows):
        overlap = False
        for pr in range(piece_rows):
            for pc in range(piece_cols):
                if piece[pr][pc] != 0:
                    if r + pr >= rows or new_board[r + pr][start_col + pc] != 0:
                        overlap = True
                        break
            if overlap:
                break
        if overlap:
            drop_row = r - 1
            break
    else:
        drop_row = rows - piece_rows

    if drop_row < 0:
        return None, 0

    for pr in range(piece_rows):
        for pc in range(piece_cols):
            if piece[pr][pc] != 0:
                new_board[drop_row + pr][start_col + pc] = 1

    lines_cleared = 0
    final_board = []
    for r in range(rows):
        if all(cell != 0 for cell in new_board[r]):
            lines_cleared += 1
        else:
            final_board.append(new_board[r])
    final_board = [[0] * cols for _ in range(lines_cleared)] + final_board

    return final_board, lines_cleared


def find_best_move(state, weights: dict, time_limit_ms: float = 75.0) -> Tuple[float, int, int]:
    start_time = time.perf_counter()
    board = getattr(state, 'board', [])
    if not board:
        return -float('inf'), 0, 0

    current_piece_type = getattr(state, 'current_piece', (1, 0))[0]
    next_queue = getattr(state, 'next_queue', [])

    best_score = -float('inf')
    best_rot, best_col = 0, 0

    current_rotations = get_all_rotations(current_piece_type)

    for rot_idx, rot_piece in enumerate(current_rotations):
        piece_cols = len(rot_piece[0])
        for col in range(len(board[0]) - piece_cols + 1):

            if (time.perf_counter() - start_time) * 1000 > time_limit_ms:
                return best_score, best_rot, best_col

            mid_board, lines_cleared_1 = simulate_drop(board, rot_piece, col)
            if mid_board is None:
                continue

            if not next_queue:
                features = evaluate_state(mid_board, lines_cleared_1)
                score = sum(weights.get(k, 0) * v for k, v in features.items())
                if score > best_score:
                    best_score, best_rot, best_col = score, rot_idx, col
                continue

            next_piece_type = next_queue[0]
            next_rotations = get_all_rotations(next_piece_type)
            best_next_score = -float('inf')

            for next_rot in next_rotations:
                next_cols = len(next_rot[0])
                for next_col in range(len(board[0]) - next_cols + 1):
                    if (time.perf_counter() - start_time) * 1000 > time_limit_ms:
                        break

                    final_board, lines_cleared_2 = simulate_drop(mid_board, next_rot, next_col)
                    if final_board is None:
                        continue

                    features = evaluate_state(final_board, lines_cleared_1 + lines_cleared_2)
                    score = sum(weights.get(k, 0) * v for k, v in features.items())
                    if score > best_next_score:
                        best_next_score = score

            if best_next_score > best_score:
                best_score, best_rot, best_col = best_next_score, rot_idx, col

    return best_score, best_rot, best_col
