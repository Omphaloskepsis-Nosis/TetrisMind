import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contracts import Action, Engine, State

DEFAULT_ACTIONS = [Action.NOOP] * 20


class ReplayPlayer:
    def __init__(self, engine: Engine, speed: int = 1, seed: int = 0):
        self.engine = engine
        self.speed = max(1, int(speed))
        self.seed = seed
        self.actions: list[Action] = list(DEFAULT_ACTIONS)
        self._action_index = 0
        self._state: State | None = None
        self.paused: bool = False

    def load_file(self, path: str | Path) -> None:
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.seed = int(data.get("seed", 0))
        raw_actions = data.get("actions", [])
        self.actions = [self._decode_action(a) for a in raw_actions]
        self._action_index = 0
        self.engine.seed = self.seed
        self._state = None
        self.paused = False

    @staticmethod
    def _decode_action(raw) -> Action:
        if isinstance(raw, str):
            try:
                return Action[raw.upper()]
            except KeyError:
                return Action.NOOP
        if isinstance(raw, int):
            try:
                return Action(raw)
            except ValueError:
                return Action.NOOP
        return Action.NOOP

    def reset(self) -> State:
        self._action_index = 0
        self._state = self.engine.reset()
        self.paused = False
        return self._state

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def restart(self) -> State:
        return self.reset()

    def set_speed(self, speed: int) -> None:
        self.speed = max(1, int(speed))

    def step_frame(self) -> State:
        if self._state is None:
            self._state = self.engine.reset()
        if self.paused:
            return self._state
        for _ in range(self.speed):
            if self._action_index >= len(self.actions):
                break
            action = self.actions[self._action_index]
            self._state = self.engine.step(action)
            self._action_index += 1
        return self._state

    @property
    def finished(self) -> bool:
        return self._action_index >= len(self.actions)

    @property
    def total_actions(self) -> int:
        return len(self.actions)

    @property
    def current_index(self) -> int:
        return self._action_index