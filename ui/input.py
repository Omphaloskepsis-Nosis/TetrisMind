import sys
import time
from enum import Enum
from pathlib import Path

import pygame

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contracts import Action, State


class InputMode(Enum):
    HUMAN = "human"
    AI = "ai"
    REPLAY = "replay"


KEY_MAP = {
    pygame.K_LEFT: Action.LEFT,
    pygame.K_RIGHT: Action.RIGHT,
    pygame.K_DOWN: Action.DOWN,
    pygame.K_UP: Action.ROTATE,
    pygame.K_x: Action.ROTATE,
    pygame.K_SPACE: Action.HARD_DROP,
    pygame.K_c: Action.HOLD,
    pygame.K_LSHIFT: Action.HOLD,
}

# 修饰键列表（忽略这些键的DEBUG日志）
_MODIFIER_KEYS = {
    pygame.K_LMETA, pygame.K_RMETA,
    pygame.K_LALT, pygame.K_RALT,
    pygame.K_LCTRL, pygame.K_RCTRL,
    pygame.K_LSHIFT, pygame.K_RSHIFT,
    pygame.K_CAPSLOCK, pygame.K_NUMLOCK,
    pygame.K_SCROLLOCK, pygame.K_MODE,
}

_HOLD_COOLDOWN_MS = 200  # HOLD键防抖冷却时间（毫秒）


_HUMAN_AI_CYCLE = [InputMode.HUMAN, InputMode.AI]


def _load_ai_policy():
    try:
        from ai.policy import policy
        print("[input] AI policy loaded.")
        return policy
    except Exception as exc:
        print(f"[input] AI policy import failed ({exc}), degraded to NOOP.")
        return lambda state, weights=None: Action.NOOP


class InputHandler:
    def __init__(self, mode: InputMode):
        self._mode = mode
        self._ai_policy = _load_ai_policy()
        self._prev_tab = False
        self._last_hold_time = 0  # 记录上一次HOLD键触发时间（毫秒）

    @property
    def mode(self) -> InputMode:
        return self._mode

    @property
    def mode_name(self) -> str:
        return self._mode.value.upper()

    def poll_events(self, events: list | None = None) -> None:
        events = events or []
        tab_pressed = any(
            e.type == pygame.KEYDOWN and e.key == pygame.K_TAB for e in events
        )
        if tab_pressed and not self._prev_tab:
            self._cycle_mode()
        self._prev_tab = tab_pressed

    def _cycle_mode(self) -> None:
        idx = _HUMAN_AI_CYCLE.index(self._mode) if self._mode in _HUMAN_AI_CYCLE else 0
        self._mode = _HUMAN_AI_CYCLE[(idx + 1) % len(_HUMAN_AI_CYCLE)]

    def _is_hold_action(self, action: Action) -> bool:
        return action == Action.HOLD

    def get_action(self, state: State | None = None, events: list | None = None) -> Action:
        self.poll_events(events)
        if self._mode == InputMode.HUMAN:
            return self._human_action(events or [])
        if self._mode == InputMode.AI:
            return self._ai_action(state)
        return Action.NOOP

    def _human_action(self, events: list) -> Action:
        now_ms = pygame.time.get_ticks()
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in KEY_MAP:
                    action = KEY_MAP[event.key]
                    if self._is_hold_action(action):
                        if now_ms - self._last_hold_time < _HOLD_COOLDOWN_MS:
                            return Action.NOOP
                        self._last_hold_time = now_ms
                    return action
                elif event.key not in _MODIFIER_KEYS:
                    print(f"[DEBUG] Key pressed but not in KEY_MAP: {event.key} ({pygame.key.name(event.key)})")
        return Action.NOOP

    def _ai_action(self, state: State | None) -> Action:
        if state is None:
            return Action.NOOP
        try:
            action = self._ai_policy(state)
            if isinstance(action, Action):
                return action
        except Exception:
            pass
        return Action.NOOP
