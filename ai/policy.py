from __future__ import annotations

from contracts import State, Action
from ai.search import find_best_move, get_all_rotations

DEFAULT_WEIGHTS = {
    "lines_cleared": 10.0,
    "holes": -7.0,
    "bumpiness": -2.0,
    "aggregate_height": -1.0,
    "row_transitions": -3.0,
    "col_transitions": -3.0
}


_TARGET_CACHE: dict[tuple, tuple[float, int, int]] = {}


def _board_key(state: State, weights: dict, time_limit_ms: float) -> tuple:
    board = tuple(tuple(row) for row in state.board)
    weight_key = tuple(sorted((key, float(value)) for key, value in weights.items()))
    return board, state.current_piece[0], tuple(state.next_queue), weight_key, time_limit_ms


def policy(
    state: State,
    weights: dict | None = None,
    time_limit_ms: float = 75.0,
) -> Action:
    if weights is None:
        weights = DEFAULT_WEIGHTS

    if state is None:
        print("[AI Warning] 传入的 State 为 None，触发降级机制，返回 NOOP。")
        return Action.NOOP

    try:
        key = _board_key(state, weights, time_limit_ms)
        target = _TARGET_CACHE.get(key)
        if target is None:
            target = find_best_move(state, weights, time_limit_ms=time_limit_ms)
            if len(_TARGET_CACHE) > 512:
                _TARGET_CACHE.clear()
            _TARGET_CACHE[key] = target
        _, target_rot, target_col = target

        piece_type, rotation = state.current_piece
        rotations = get_all_rotations(piece_type)
        rotation_count = max(1, len(rotations))
        if target_rot % rotation_count != rotation % rotation_count:
            return Action.ROTATE

        shape = rotations[target_rot % rotation_count]
        min_col = min(
            col
            for row in shape
            for col, value in enumerate(row)
            if value
        )
        physical_col = max(0, target_col - min_col)
        current_x = getattr(state, "current_piece", (piece_type, 0))[1]
        current_cells = getattr(state, "current_cells", [])
        if current_cells:
            current_x = min(x for x, _ in current_cells)

        if current_x < physical_col:
            return Action.RIGHT
        if current_x > physical_col:
            return Action.LEFT
        return Action.HARD_DROP

    except Exception as e:
        print(f"[AI Warning] 决策异常降级 NOOP: {e}")
        return Action.NOOP
