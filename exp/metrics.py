"""Stable result objects shared by the runner, GA, tests, and report."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


WEIGHT_NAMES = (
    "lines_cleared",
    "holes",
    "bumpiness",
    "aggregate_height",
    "row_transitions",
    "col_transitions",
)

# These names and signs match P3's six evaluation features exactly.
DEFAULT_WEIGHTS: dict[str, float] = {
    "lines_cleared": 10.0,
    "holes": -7.0,
    "bumpiness": -2.0,
    "aggregate_height": -1.0,
    "row_transitions": -3.0,
    "col_transitions": -3.0,
}


@dataclass(frozen=True)
class Metrics:
    """Aggregate result returned by ``evaluate``.

    ``game_lines`` and ``game_scores`` retain per-game observations so callers
    can calculate paired comparisons instead of comparing only two averages.
    """

    name: str
    seed: int
    games: int
    lines_mean: float
    lines_std: float
    score_mean: float
    score_std: float
    pieces_mean: float
    elapsed_ms_mean: float
    fitness: float
    backend: str
    weights: dict[str, float]
    game_lines: tuple[int, ...]
    game_scores: tuple[int, ...]

    @property
    def average_lines(self) -> float:
        """Compatibility alias used by early P3/P4 prototypes."""

        return self.lines_mean

    @property
    def mean_lines(self) -> float:
        return self.lines_mean

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["average_lines"] = self.lines_mean
        result["mean_lines"] = self.lines_mean
        return result


def mean_and_std(values: Iterable[float]) -> tuple[float, float]:
    numbers = [float(value) for value in values]
    if not numbers:
        return 0.0, 0.0
    mean = sum(numbers) / len(numbers)
    variance = sum((value - mean) ** 2 for value in numbers) / len(numbers)
    return mean, variance**0.5


def metrics_from_games(
    games: list[dict[str, float | int]],
    *,
    name: str,
    seed: int,
    weights: dict[str, float],
    backend: str,
) -> Metrics:
    line_values = [int(game["lines"]) for game in games]
    score_values = [int(game["score"]) for game in games]
    piece_values = [int(game["pieces"]) for game in games]
    elapsed_values = [float(game["elapsed_ms"]) for game in games]
    lines_mean, lines_std = mean_and_std(line_values)
    score_mean, score_std = mean_and_std(score_values)
    pieces_mean, _ = mean_and_std(piece_values)
    elapsed_mean, _ = mean_and_std(elapsed_values)

    # Lines remain the primary acceptance criterion. A small score term breaks
    # ties between policies that clear the same number of lines.
    fitness = lines_mean + 0.005 * score_mean
    return Metrics(
        name=name,
        seed=seed,
        games=len(games),
        lines_mean=lines_mean,
        lines_std=lines_std,
        score_mean=score_mean,
        score_std=score_std,
        pieces_mean=pieces_mean,
        elapsed_ms_mean=elapsed_mean,
        fitness=fitness,
        backend=backend,
        weights={key: float(value) for key, value in weights.items()},
        game_lines=tuple(line_values),
        game_scores=tuple(score_values),
    )
