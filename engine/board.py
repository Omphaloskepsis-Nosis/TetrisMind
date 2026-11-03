"""Board and tetromino primitives for TetrisMind.

Coordinates: x grows right, y grows down. The board stores only its visible
rows; pieces may occupy negative y during spawning, but locking above the
board is treated as game over.
"""
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple
import copy

Point = Tuple[int, int]

# SRS spawn-state cell coordinates. JLSTZ use a 3x3 box with pivot (1, 1);
# I/O use a 4x4 box with pivot (1.5, 1.5).
SPAWN_CELLS = {
    "I": ((0, 1), (1, 1), (2, 1), (3, 1)),
    "O": ((1, 0), (2, 0), (1, 1), (2, 1)),
    "T": ((0, 1), (1, 1), (2, 1), (1, 0)),
    "S": ((1, 0), (2, 0), (0, 1), (1, 1)),
    "Z": ((0, 0), (1, 0), (1, 1), (2, 1)),
    "J": ((0, 0), (0, 1), (1, 1), (2, 1)),
    "L": ((2, 0), (0, 1), (1, 1), (2, 1)),
}

PIECE_NAMES = tuple(SPAWN_CELLS.keys())


@dataclass
class Piece:
    kind: str
    x: int
    y: int
    rotation: int = 0

    def clone(self) -> "Piece":
        return copy.copy(self)

    @property
    def cells(self) -> Tuple[Point, ...]:
        """Return absolute occupied cells for the current rotation."""
        return tuple((self.x + dx, self.y + dy)
                     for dx, dy in rotation_cells(self.kind, self.rotation))


def _rotate_point(point: Point, kind: str, turns: int) -> Point:
    """Rotate a spawn cell clockwise around the SRS pivot."""
    x, y = point
    if kind == "I":
        # 4x4 SRS box, pivot (1.5, 1.5); doubled coordinates avoid floats.
        for _ in range(turns % 4):
            x, y = 3 - y, x
    elif kind == "O":
        return point
    else:
        # 3x3 SRS box, pivot (1, 1).
        for _ in range(turns % 4):
            x, y = 2 - y, x
    return x, y


def rotation_cells(kind: str, rotation: int) -> Tuple[Point, ...]:
    if kind not in SPAWN_CELLS:
        raise ValueError(f"Unknown tetromino: {kind!r}")
    turns = rotation % 4
    return tuple(_rotate_point(p, kind, turns) for p in SPAWN_CELLS[kind])


class Board:
    def __init__(self, width: int = 10, height: int = 20):
        if width < 4 or height < 4:
            raise ValueError("Board dimensions must be at least 4.")
        self.width = width
        self.height = height
        self.grid: List[List[Optional[str]]] = [
            [None for _ in range(width)] for _ in range(height)
        ]

    def clone(self) -> "Board":
        other = Board(self.width, self.height)
        other.grid = copy.deepcopy(self.grid)
        return other

    def is_valid(self, piece: Piece) -> bool:
        for x, y in piece.cells:
            if x < 0 or x >= self.width or y >= self.height:
                return False
            if y >= 0 and self.grid[y][x] is not None:
                return False
        return True

    def lock(self, piece: Piece) -> None:
        """Merge a piece into the board. Raises ValueError on overlap/top-out."""
        if not self.is_valid(piece):
            raise ValueError("Cannot lock an invalid piece.")
        if any(y < 0 for _, y in piece.cells):
            raise ValueError("Piece locked above the visible board (top-out).")
        for x, y in piece.cells:
            self.grid[y][x] = piece.kind

    def clear_lines(self) -> int:
        """Remove full rows and prepend empty rows; return number cleared."""
        remaining = [row for row in self.grid if not all(v is not None for v in row)]
        cleared = self.height - len(remaining)
        if cleared:
            self.grid = (
                [[None for _ in range(self.width)] for _ in range(cleared)]
                + remaining
            )
        return cleared

    def column_heights(self) -> List[int]:
        heights = []
        for x in range(self.width):
            occupied = [y for y in range(self.height) if self.grid[y][x] is not None]
            heights.append(self.height - min(occupied) if occupied else 0)
        return heights

    def count_holes(self) -> int:
        holes = 0
        for x in range(self.width):
            seen_block = False
            for y in range(self.height):
                if self.grid[y][x] is not None:
                    seen_block = True
                elif seen_block:
                    holes += 1
        return holes

    def aggregate_height(self) -> int:
        return sum(self.column_heights())

    def bumpiness(self) -> int:
        heights = self.column_heights()
        return sum(abs(heights[i] - heights[i + 1])
                   for i in range(self.width - 1))

    def is_empty(self) -> bool:
        return all(cell is None for row in self.grid for cell in row)

    def __str__(self) -> str:
        return "\n".join(
            "|" + "".join("." if c is None else c for c in row) + "|"
            for row in self.grid
        )
