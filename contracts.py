"""Integration contract shared by the rule engine, UI, AI, and experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from engine import Game


class Action(Enum):
    LEFT = auto()
    RIGHT = auto()
    DOWN = auto()
    ROTATE = auto()
    HARD_DROP = auto()
    HOLD = auto()
    NOOP = auto()


@dataclass
class State:
    board: list[list[int]]
    current_piece: tuple[int, int]
    hold_piece: Optional[int]
    next_queue: list[int]
    cleared_lines: list[int]
    score: int = 0
    level: int = 1
    total_lines: int = 0
    current_cells: list[tuple[int, int]] = field(default_factory=list)
    current_kind: int = 0
    game_over: bool = False
    combo: int = -1
    back_to_back: bool = False
    piece_count: int = 0
    last_clear: dict = field(default_factory=dict)


PIECE_NAME_TO_ID = {
    "I": 1,
    "O": 2,
    "T": 3,
    "J": 4,
    "L": 5,
    "S": 6,
    "Z": 7,
}
PIECE_ID_TO_NAME = {value: key for key, value in PIECE_NAME_TO_ID.items()}


class Engine:
    """Adapt P1's Game API to the Action/State contract used by P2-P4."""

    def __init__(self, seed: int = 0):
        self.seed = int(seed)
        self.game = Game(seed=self.seed)
        self.piece_count = 0

    def reset(self) -> State:
        self.game = Game(seed=self.seed)
        self.piece_count = 0
        return self.snapshot()

    def step(self, action: Action) -> State:
        if self.game.game_over:
            return self.snapshot()
        if not isinstance(action, Action):
            return self.snapshot()

        action_names = {
            Action.LEFT: "left",
            Action.RIGHT: "right",
            Action.DOWN: "soft_drop",
            Action.ROTATE: "rotate_cw",
            Action.HARD_DROP: "hard_drop",
            Action.HOLD: "hold",
        }
        name = action_names.get(action)
        if name is not None:
            self.game.apply_action(name)
            if action == Action.HARD_DROP and not self.game.game_over:
                self.piece_count += 1
        return self.snapshot()

    def auto_step(self, weights: dict | None = None, time_limit_ms: float = 12.0) -> State:
        """Let P3 place one complete piece, then return the locked snapshot."""

        from ai.policy import policy

        initial_board = self._board_signature()
        previous_state = None
        for _ in range(40):
            state = self.snapshot()
            if state.game_over:
                return state
            signature = (
                tuple(state.current_piece),
                tuple(state.current_cells),
                state.score,
            )
            if signature == previous_state:
                # A policy that cannot change state should not spin forever.
                self.step(Action.HARD_DROP)
                return self.snapshot()
            previous_state = signature
            action = policy(state, weights, time_limit_ms=time_limit_ms)
            self.step(action)
            if self._board_signature() != initial_board or self.game.game_over:
                return self.snapshot()
        self.step(Action.HARD_DROP)
        return self.snapshot()

    def _board_signature(self) -> tuple[tuple[str | None, ...], ...]:
        return tuple(tuple(row) for row in self.game.board.grid)

    def snapshot(self) -> State:
        raw = self.game.get_state()
        board = [
            [PIECE_NAME_TO_ID.get(cell, 0) if cell is not None else 0 for cell in row]
            for row in raw["board"]
        ]
        current = raw["current"]
        piece_id = PIECE_NAME_TO_ID[current["kind"]]
        hold = raw["hold"]
        last_clear = dict(self.game.last_clear)
        return State(
            board=board,
            current_piece=(piece_id, int(current["rotation"])),
            hold_piece=PIECE_NAME_TO_ID.get(hold),
            next_queue=[PIECE_NAME_TO_ID[kind] for kind in raw["next"]],
            cleared_lines=[],
            score=int(raw["score"]),
            level=int(raw["level"]),
            total_lines=int(raw["lines"]),
            current_cells=[(int(x), int(y)) for x, y in current["cells"]],
            current_kind=piece_id,
            game_over=bool(raw["game_over"]),
            combo=int(raw["combo"]),
            back_to_back=bool(raw["back_to_back"]),
            piece_count=self.piece_count,
            last_clear=last_clear,
        )

    def get_state(self) -> State:
        return self.snapshot()
