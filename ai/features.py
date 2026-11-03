from typing import List


def get_column_heights(board: List[List[int]]) -> List[int]:
    heights = [0] * len(board[0])
    for c in range(len(board[0])):
        for r in range(len(board)):
            if board[r][c] != 0:
                heights[c] = len(board) - r
                break
    return heights


def count_holes(board: List[List[int]], heights: List[int]) -> int:
    holes = 0
    for c in range(len(board[0])):
        first_block = len(board) - heights[c]
        for r in range(first_block + 1, len(board)):
            if board[r][c] == 0:
                holes += 1
    return holes


def calc_bumpiness(heights: List[int]) -> int:
    return sum(abs(heights[i] - heights[i + 1]) for i in range(len(heights) - 1))


def calc_row_transitions(board: List[List[int]]) -> int:
    transitions = 0
    for r in range(len(board)):
        row = board[r]
        prev = 1
        for c in range(len(board[0])):
            curr = 1 if row[c] != 0 else 0
            if curr != prev:
                transitions += 1
            prev = curr
        if prev == 0:
            transitions += 1
    return transitions


def calc_col_transitions(board: List[List[int]], heights: List[int]) -> int:
    transitions = 0
    for c in range(len(board[0])):
        col_trans = 0
        prev = 0
        for r in range(len(board) - heights[c], len(board)):
            curr = 1 if board[r][c] != 0 else 0
            if curr != prev:
                col_trans += 1
            prev = curr
        if prev == 0:
            col_trans += 1
        transitions += col_trans
    return transitions


def evaluate_state(board: List[List[int]], lines_cleared: int) -> dict:
    heights = get_column_heights(board)
    return {
        "lines_cleared": lines_cleared,
        "holes": count_holes(board, heights),
        "bumpiness": calc_bumpiness(heights),
        "aggregate_height": sum(heights),
        "row_transitions": calc_row_transitions(board),
        "col_transitions": calc_col_transitions(board, heights)
    }
