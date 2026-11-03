"""Batch game runner and the public ``evaluate`` interface."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import importlib
from typing import Any, Callable

from exp.metrics import Metrics, metrics_from_games, DEFAULT_WEIGHTS
from exp.reference import normalise_weights, run_reference_game


def _load_callable(spec: str, default_name: str) -> Callable[..., Any]:
    module_name, separator, attribute = spec.partition(":")
    if not separator:
        attribute = default_name
    module = importlib.import_module(module_name)
    return getattr(module, attribute)


def detect_backend() -> str:
    """Use P1/P3 when both modules exist, otherwise use the fallback."""

    try:
        importlib.import_module("ai.policy")
    except (ImportError, ModuleNotFoundError):
        return "reference"
    return "external"


def _is_terminal(state: Any, engine: Any) -> bool:
    for owner in (state, engine):
        for name in ("game_over", "done", "is_over", "terminal"):
            value = getattr(owner, name, None)
            if callable(value):
                try:
                    value = value()
                except TypeError:
                    continue
            if isinstance(value, bool):
                return value
        status = getattr(owner, "status", None)
        if isinstance(status, str) and status.lower() in {"over", "game_over", "finished"}:
            return True
    return False


def _numeric_state_field(state: Any, engine: Any, names: tuple[str, ...]) -> float:
    for owner in (state, engine):
        for name in names:
            value = getattr(owner, name, None)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
    return 0.0


def run_external_game(
    weights: dict[str, float],
    seed: int,
    max_pieces: int = 120,
    *,
    engine_spec: str = "contracts:Engine",
    policy_spec: str = "ai.policy:policy",
) -> dict[str, float | int]:
    """Run P1 Engine with P3 policy through the frozen module contract."""

    import time

    engine_class = _load_callable(engine_spec, "Engine")
    policy = _load_callable(policy_spec, "policy")
    try:
        engine = engine_class(seed=seed)
    except TypeError:
        engine = engine_class(seed)
    state = engine.reset()

    started = time.perf_counter()
    steps = 0
    # Micro-actions mean a piece may take many Engine.step calls. This cap only
    # protects against a NOOP policy; normal games terminate much earlier.
    max_steps = max(2000, max_pieces * 250)
    while steps < max_steps and not _is_terminal(state, engine):
        try:
            action = policy(state, weights)
        except TypeError:
            action = policy(state)
        state = engine.step(action)
        steps += 1
        pieces = _numeric_state_field(state, engine, ("pieces", "piece_count"))
        if pieces >= max_pieces:
            break

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return {
        "seed": seed,
        "lines": int(_numeric_state_field(state, engine, ("total_lines", "lines_cleared", "lines"))),
        "score": int(_numeric_state_field(state, engine, ("score",))),
        "pieces": int(_numeric_state_field(state, engine, ("pieces", "piece_count"))),
        "elapsed_ms": elapsed_ms,
    }


def _run_one_game(payload: tuple[dict[str, float], int, int, str, str, str]) -> dict[str, float | int]:
    weights, seed, max_pieces, backend, engine_spec, policy_spec = payload
    if backend == "reference":
        return run_reference_game(weights, seed, max_pieces)
    return run_external_game(
        weights,
        seed,
        max_pieces,
        engine_spec=engine_spec,
        policy_spec=policy_spec,
    )


def evaluate_serial(
    weights: dict[str, float] | None,
    seed: int,
    n: int,
    *,
    name: str = "evaluation",
    backend: str = "auto",
    max_pieces: int = 120,
    engine_spec: str = "contracts:Engine",
    policy_spec: str = "ai.policy:policy",
) -> Metrics:
    if n <= 0:
        raise ValueError("n must be a positive integer")
    selected_backend = detect_backend() if backend == "auto" else backend
    if selected_backend not in {"reference", "external"}:
        raise ValueError("backend must be 'auto', 'reference', or 'external'")
    normalised = normalise_weights(weights)
    games = [
        _run_one_game(
            (normalised, seed + index, max_pieces, selected_backend, engine_spec, policy_spec)
        )
        for index in range(n)
    ]
    return metrics_from_games(
        games,
        name=name,
        seed=seed,
        weights=normalised,
        backend=selected_backend,
    )


def evaluate(
    weights: dict[str, float] | None = None,
    seed: int = 42,
    n: int = 1,
    *,
    name: str = "evaluation",
    backend: str = "auto",
    workers: int = 1,
    max_pieces: int = 120,
    engine_spec: str = "contracts:Engine",
    policy_spec: str = "ai.policy:policy",
) -> Metrics:
    """Evaluate one weight vector over ``n`` deterministic games.

    Game ``i`` uses ``seed + i``. Passing the same seed/game count to baseline
    and tuned policies therefore produces paired comparisons.
    """

    if workers <= 1 or n <= 1:
        return evaluate_serial(
            weights,
            seed,
            n,
            name=name,
            backend=backend,
            max_pieces=max_pieces,
            engine_spec=engine_spec,
            policy_spec=policy_spec,
        )

    if n <= 0:
        raise ValueError("n must be a positive integer")
    selected_backend = detect_backend() if backend == "auto" else backend
    if selected_backend not in {"reference", "external"}:
        raise ValueError("backend must be 'auto', 'reference', or 'external'")
    normalised = normalise_weights(weights)
    payloads = [
        (normalised, seed + index, max_pieces, selected_backend, engine_spec, policy_spec)
        for index in range(n)
    ]
    with ProcessPoolExecutor(max_workers=min(workers, n)) as executor:
        games = list(executor.map(_run_one_game, payloads))
    games.sort(key=lambda game: int(game["seed"]))
    return metrics_from_games(
        games,
        name=name,
        seed=seed,
        weights=normalised,
        backend=selected_backend,
    )
