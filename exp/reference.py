"""Deterministic fallback Tetris environment for standalone P4 development.

The production path in :mod:`exp.runner` prefers P1's Engine and P3's policy.
This compact environment keeps P4 demonstrable before those modules are merged
and uses the same six heuristic dimensions expected by the experiment layer.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
import time
from typing import Iterable

from exp.metrics import DEFAULT_WEIGHTS, WEIGHT_NAMES


COLS = 10
ROWS = 20
FULL_ROW = (1 << COLS) - 1


def normalize_shape(cells: Iterable[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    points = set(cells)
    min_row = min(row for row, _ in points)
    min_col = min(col for _, col in points)
    return tuple(sorted((row - min_row, col - min_col) for row, col in points))


def rotate_shape(cells: tuple[tuple[int, int], ...]) -> tuple[tuple[int, int], ...]:
    # (row, col) -> (col, -row), then normalize back into the positive quadrant.
    return normalize_shape((col, -row) for row, col in cells)


BASE_SHAPES: dict[str, tuple[tuple[int, int], ...]] = {
    "I": ((0, 0), (0, 1), (0, 2), (0, 3)),
    "O": ((0, 0), (0, 1), (1, 0), (1, 1)),
    "T": ((0, 0), (0, 1), (0, 2), (1, 1)),
    "S": ((0, 1), (0, 2), (1, 0), (1, 1)),
    "Z": ((0, 0), (0, 1), (1, 1), (1, 2)),
    "J": ((0, 0), (1, 0), (1, 1), (1, 2)),
    "L": ((0, 2), (1, 0), (1, 1), (1, 2)),
}


def unique_rotations(shape: tuple[tuple[int, int], ...]) -> tuple[tuple[tuple[int, int], ...], ...]:
    rotations: list[tuple[tuple[int, int], ...]] = []
    current = normalize_shape(shape)
    for _ in range(4):
        if current not in rotations:
            rotations.append(current)
        current = rotate_shape(current)
    return tuple(rotations)


SHAPES = {name: unique_rotations(cells) for name, cells in BASE_SHAPES.items()}


@dataclass(frozen=True)
class Placement:
    board: tuple[int, ...]
    cleared: int
    landing_height: float
    holes: int
    aggregate_height: int
    bumpiness: int
    wells: int


def board_features(board: tuple[int, ...] | list[int]) -> tuple[int, int, int, int]:
    heights: list[int] = []
    holes = 0
    for col in range(COLS):
        bit = 1 << col
        top_row = None
        column_holes = 0
        for row, mask in enumerate(board):
            if mask & bit:
                if top_row is None:
                    top_row = row
            elif top_row is not None:
                column_holes += 1
        holes += column_holes
        heights.append(ROWS - top_row if top_row is not None else 0)

    bumpiness = sum(abs(left - right) for left, right in zip(heights, heights[1:]))
    wells = 0
    for col, height in enumerate(heights):
        left = heights[col - 1] if col > 0 else ROWS
        right = heights[col + 1] if col + 1 < COLS else ROWS
        wells += max(0, min(left, right) - height)
    return holes, sum(heights), bumpiness, wells


def _clear_rows(rows: list[int]) -> tuple[tuple[int, ...], int]:
    kept = [row for row in rows if row != FULL_ROW]
    cleared = ROWS - len(kept)
    return tuple([0] * cleared + kept), cleared


def enumerate_placements(board: tuple[int, ...], piece: str) -> list[Placement]:
    placements: list[Placement] = []
    for rotation in SHAPES[piece]:
        width = max(col for _, col in rotation) + 1
        height = max(row for row, _ in rotation) + 1
        for x in range(COLS - width + 1):
            y = 0
            while True:
                next_y = y + 1
                if next_y + height > ROWS:
                    break
                collision = False
                for row, col in rotation:
                    if board[next_y + row] & (1 << (x + col)):
                        collision = True
                        break
                if collision:
                    break
                y = next_y

            collision = any(board[y + row] & (1 << (x + col)) for row, col in rotation)
            if collision:
                continue

            rows = list(board)
            for row, col in rotation:
                rows[y + row] |= 1 << (x + col)
            new_board, cleared = _clear_rows(rows)
            if new_board[0] and not cleared:
                # This placement top-outs immediately and is not useful.
                continue
            holes, total_height, bumpiness, wells = board_features(new_board)
            placements.append(
                Placement(
                    board=new_board,
                    cleared=cleared,
                    landing_height=max(y + row for row, _ in rotation),
                    holes=holes,
                    aggregate_height=total_height,
                    bumpiness=bumpiness,
                    wells=wells,
                )
            )
    return placements


def placement_score(placement: Placement, weights: dict[str, float]) -> float:
    return (
        float(weights.get("lines", 0.0)) * placement.cleared
        - float(weights.get("holes", 0.0)) * placement.holes
        - float(weights.get("height", 0.0)) * placement.aggregate_height
        - float(weights.get("bumpiness", 0.0)) * placement.bumpiness
        - float(weights.get("wells", 0.0)) * placement.wells
        - float(weights.get("landing_height", 0.0)) * placement.landing_height
    )


def run_reference_game(
    weights: dict[str, float],
    seed: int,
    max_pieces: int = 120,
) -> dict[str, float | int]:
    """Play one deterministic game using the current heuristic weights."""

    started = time.perf_counter()
    rng = random.Random(seed)
    board: tuple[int, ...] = (0,) * ROWS
    lines = 0
    pieces = 0
    score = 0
    line_scores = (0, 100, 300, 500, 800)
    bag: list[str] = []

    while pieces < max_pieces:
        if not bag:
            bag = list(SHAPES)
            rng.shuffle(bag)
        piece = bag.pop()
        placements = enumerate_placements(board, piece)
        if not placements:
            break

        # Stable tie-breaking prevents seed drift across Python versions.
        best_score = max(placement_score(placement, weights) for placement in placements)
        candidates = [
            placement
            for placement in placements
            if abs(placement_score(placement, weights) - best_score) < 1e-9
        ]
        chosen = min(
            candidates,
            key=lambda item: (
                item.holes,
                item.aggregate_height,
                item.bumpiness,
                item.wells,
            ),
        )
        board = chosen.board
        lines += chosen.cleared
        score += line_scores[min(chosen.cleared, 4)]
        pieces += 1
        if board[0]:
            break

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return {
        "seed": seed,
        "lines": lines,
        "score": score,
        "pieces": pieces,
        "elapsed_ms": elapsed_ms,
    }


def normalise_weights(weights: dict[str, float] | None = None) -> dict[str, float]:
    source = weights or DEFAULT_WEIGHTS
    return {name: float(source.get(name, DEFAULT_WEIGHTS[name])) for name in WEIGHT_NAMES}
