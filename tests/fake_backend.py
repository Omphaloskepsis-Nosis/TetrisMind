"""Minimal engine/policy stand-ins used to verify the optional integration adapter."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class Action(Enum):
    DOWN = auto()


@dataclass
class State:
    board: list[list[int]]
    total_lines: int
    score: int
    piece_count: int
    game_over: bool


class Engine:
    def __init__(self, seed: int = 0):
        self.seed = seed
        self._steps = 0

    def reset(self) -> State:
        self._steps = 0
        return State(
            board=[[0] * 10 for _ in range(20)],
            total_lines=0,
            score=0,
            piece_count=0,
            game_over=False,
        )

    def step(self, action: Action) -> State:
        self._steps += 1
        finished = self._steps >= 6
        return State(
            board=[[0] * 10 for _ in range(20)],
            total_lines=1 if finished else 0,
            score=100 if finished else 0,
            piece_count=max(1, self._steps // 3),
            game_over=finished,
        )


def policy(state: State, weights: dict[str, float] | None = None) -> Action:
    return Action.DOWN
