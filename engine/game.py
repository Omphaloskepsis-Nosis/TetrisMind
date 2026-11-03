"""Game controller for TetrisMind.

Public controls: move_left/right, soft_drop, hard_drop, rotate_cw/ccw, hold.
The engine is deterministic when initialized with a seeded random.Random.
"""
from collections import deque
import random
from typing import Deque, Dict, List, Optional, Tuple

from .board import Board, Piece, PIECE_NAMES
from .srs import try_rotate


class Game:
    # Guideline-style base scores, multiplied by current level.
    LINE_SCORES = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}
    TSPIN_SCORES = {0: 400, 1: 800, 2: 1200, 3: 1600}
    MINI_SCORES = {0: 100, 1: 200, 2: 400}

    def __init__(self, width: int = 10, height: int = 20,
                 seed: Optional[int] = None, lines_per_level: int = 10):
        self.board = Board(width, height)
        self.rng = random.Random(seed)
        self.lines_per_level = max(1, lines_per_level)
        self.bag: Deque[str] = deque()
        self.queue: Deque[str] = deque()
        self.score = 0
        self.lines = 0
        self.level = 1
        self.combo = -1
        self.back_to_back = False
        self.hold_piece: Optional[str] = None
        self.hold_used = False
        self.game_over = False
        self.last_action_was_rotation = False
        self.last_kick_index: Optional[int] = None
        self.last_clear: Dict[str, object] = {}
        self._fill_queue(7)
        self.current = self._spawn(self._pop_next())

    def _refill_bag(self) -> None:
        pieces = list(PIECE_NAMES)
        self.rng.shuffle(pieces)
        self.bag.extend(pieces)

    def _pop_next(self) -> str:
        if not self.bag:
            self._refill_bag()
        return self.bag.popleft()

    def _fill_queue(self, count: int = 5) -> None:
        while len(self.queue) < count:
            self.queue.append(self._pop_next())

    def _spawn(self, kind: str) -> Piece:
        # Spawn boxes are 3 cells wide (JLSTZ) or 4 cells wide (I/O).
        box_width = 4 if kind in ("I", "O") else 3
        x = (self.board.width - box_width) // 2
        piece = Piece(kind, x, 0, 0)
        if not self.board.is_valid(piece):
            self.game_over = True
        self.last_action_was_rotation = False
        self.last_kick_index = None
        return piece

    def _after_piece_lock(self) -> None:
        self.hold_used = False
        self.current = self._spawn(self._pop_next())
        self._fill_queue(5)
        if not self.board.is_valid(self.current):
            self.game_over = True

    def move(self, dx: int, dy: int = 0) -> bool:
        if self.game_over:
            return False
        candidate = self.current.clone()
        candidate.x += dx
        candidate.y += dy
        if self.board.is_valid(candidate):
            self.current = candidate
            # Horizontal input supersedes a rotation for T-Spin detection.
            # Downward travel (gravity / hard drop) does not: a rotated piece
            # may still be locked by a hard drop and score as a T-Spin.
            if dx != 0:
                self.last_action_was_rotation = False
                self.last_kick_index = None
            return True
        return False

    def move_left(self) -> bool:
        return self.move(-1, 0)

    def move_right(self) -> bool:
        return self.move(1, 0)

    def soft_drop(self) -> bool:
        moved = self.move(0, 1)
        if moved:
            self.score += 1
        return moved

    def rotate(self, direction: int = 1) -> bool:
        if self.game_over:
            return False
        success, kick_index = try_rotate(self.board, self.current, direction)
        if success:
            self.last_action_was_rotation = True
            self.last_kick_index = kick_index
        return success

    def rotate_cw(self) -> bool:
        return self.rotate(1)

    def rotate_ccw(self) -> bool:
        return self.rotate(-1)

    def hard_drop(self) -> int:
        """Drop to the lowest valid position, lock, score, and spawn next."""
        if self.game_over:
            return 0
        distance = 0
        while self.move(0, 1):
            distance += 1
        self.score += 2 * distance
        self.lock_piece()
        return distance

    def hold(self) -> bool:
        """Swap current piece with hold slot. Once per falling piece."""
        if self.game_over or self.hold_used:
            return False
        outgoing = self.current.kind
        if self.hold_piece is None:
            self.hold_piece = outgoing
            incoming = self._pop_next()
            self._fill_queue(5)
        else:
            incoming = self.hold_piece
            self.hold_piece = outgoing
        self.hold_used = True
        self.current = self._spawn(incoming)
        return not self.game_over

    def _is_tspin(self) -> Tuple[bool, bool]:
        """Return (is_tspin, is_mini) using the four pivot-corner test.

        Three occupied/out-of-bounds diagonal corners are required. The two
        front corners depend on orientation. A fifth-kick rotation upgrades
        a mini to a full T-Spin (SRS convention).
        """
        if self.current.kind != "T" or not self.last_action_was_rotation:
            return False, False

        # T pivot is local (1, 1) in its 3x3 SRS box.
        px, py = self.current.x + 1, self.current.y + 1

        def occupied(x: int, y: int) -> bool:
            if x < 0 or x >= self.board.width or y >= self.board.height:
                return True
            if y < 0:
                return False
            return self.board.grid[y][x] is not None

        corners = {
            "nw": occupied(px - 1, py - 1),
            "ne": occupied(px + 1, py - 1),
            "sw": occupied(px - 1, py + 1),
            "se": occupied(px + 1, py + 1),
        }
        if sum(corners.values()) < 3:
            return False, False

        front_by_rotation = {
            0: ("nw", "ne"),
            1: ("ne", "se"),
            2: ("sw", "se"),
            3: ("nw", "sw"),
        }
        front_count = sum(corners[k] for k in front_by_rotation[self.current.rotation % 4])
        mini = front_count < 2
        if self.last_kick_index == 4:
            mini = False
        return True, mini

    def lock_piece(self) -> Dict[str, object]:
        if self.game_over:
            return {}
        is_tspin, is_mini = self._is_tspin()
        try:
            self.board.lock(self.current)
        except ValueError:
            self.game_over = True
            return {}

        cleared = self.board.clear_lines()
        self.lines += cleared
        self.level = 1 + self.lines // self.lines_per_level

        difficult = cleared == 4 or (is_tspin and cleared > 0)
        base = 0
        event = "none"
        if is_tspin:
            if is_mini:
                base = self.MINI_SCORES.get(cleared, 400)
                event = "tspin_mini"
            else:
                base = self.TSPIN_SCORES.get(cleared, 1600)
                event = "tspin"
        else:
            base = self.LINE_SCORES.get(cleared, 0)
            if cleared:
                event = f"line_clear_{cleared}"

        b2b_bonus = 0
        if difficult and base:
            if self.back_to_back:
                b2b_bonus = base // 2
            self.back_to_back = True
        elif cleared > 0:
            self.back_to_back = False

        if cleared > 0:
            self.combo += 1
            combo_bonus = max(0, self.combo) * 50 * self.level
        else:
            self.combo = -1
            combo_bonus = 0

        gained = base * self.level + b2b_bonus * self.level + combo_bonus
        self.score += gained
        result = {
            "lines_cleared": cleared,
            "t_spin": is_tspin,
            "t_spin_mini": is_tspin and is_mini,
            "event": event,
            "base_score": base,
            "back_to_back_bonus": b2b_bonus * self.level,
            "combo_bonus": combo_bonus,
            "score_gained": gained,
            "score": self.score,
            "lines": self.lines,
            "level": self.level,
        }
        self.last_clear = result
        self._after_piece_lock()
        return result

    def tick(self, gravity_cells: int = 1) -> int:
        """Advance gravity by N cells; lock when the piece cannot descend."""
        if gravity_cells < 0:
            raise ValueError("gravity_cells must be non-negative")
        moved = 0
        for _ in range(gravity_cells):
            if self.move(0, 1):
                moved += 1
            else:
                self.lock_piece()
                break
        return moved

    def get_state(self) -> Dict[str, object]:
        """Return a detached, AI-friendly snapshot of the current game."""
        return {
            "board": [row[:] for row in self.board.grid],
            "width": self.board.width,
            "height": self.board.height,
            "current": {
                "kind": self.current.kind,
                "x": self.current.x,
                "y": self.current.y,
                "rotation": self.current.rotation,
                "cells": list(self.current.cells),
            },
            "next": list(self.queue),
            "hold": self.hold_piece,
            "hold_used": self.hold_used,
            "score": self.score,
            "lines": self.lines,
            "level": self.level,
            "combo": self.combo,
            "back_to_back": self.back_to_back,
            "game_over": self.game_over,
        }

    def legal_actions(self) -> List[str]:
        """Convenience action names for an AI controller."""
        if self.game_over:
            return []
        actions = ["left", "right", "soft_drop", "hard_drop",
                   "rotate_cw", "rotate_ccw"]
        if not self.hold_used:
            actions.append("hold")
        return actions

    def apply_action(self, action: str):
        """Execute one named AI action and return its result."""
        actions = {
            "left": self.move_left,
            "right": self.move_right,
            "soft_drop": self.soft_drop,
            "hard_drop": self.hard_drop,
            "rotate_cw": self.rotate_cw,
            "rotate_ccw": self.rotate_ccw,
            "hold": self.hold,
        }
        if action not in actions:
            raise ValueError(f"Unknown action: {action!r}")
        return actions[action]()
