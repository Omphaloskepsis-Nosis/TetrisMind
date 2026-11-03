"""A dependency-free genetic algorithm for six heuristic weights."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import random
from typing import Callable

from exp.metrics import DEFAULT_WEIGHTS, Metrics, WEIGHT_NAMES
from exp.runner import evaluate_serial


@dataclass(frozen=True)
class GAConfig:
    generations: int = 30
    population_size: int = 16
    games_per_candidate: int = 2
    seed: int = 42
    workers: int = 4
    max_pieces: int = 120
    elite_count: int = 2
    tournament_size: int = 3
    mutation_sigma: float = 0.35
    crossover_rate: float = 0.7
    backend: str = "auto"
    engine_spec: str = "contracts:Engine"
    policy_spec: str = "ai.policy:policy"

    def validate(self) -> None:
        if self.generations <= 0:
            raise ValueError("generations must be positive")
        if self.population_size < 4:
            raise ValueError("population_size must be at least 4")
        if self.games_per_candidate <= 0:
            raise ValueError("games_per_candidate must be positive")
        if not 0 <= self.elite_count < self.population_size:
            raise ValueError("elite_count must be between 0 and population_size - 1")


@dataclass(frozen=True)
class GenerationRecord:
    generation: int
    best_fitness: float
    mean_fitness: float
    best_lines: float
    best_weights: dict[str, float]


@dataclass
class GAResult:
    best_weights: dict[str, float]
    best_metrics: Metrics
    history: list[GenerationRecord]
    config: GAConfig


# Positive/negative signs express whether a feature is encouraged or penalized.
LOWER_BOUNDS = {
    "lines_cleared": 0.0,
    "holes": -20.0,
    "bumpiness": -8.0,
    "aggregate_height": -4.0,
    "row_transitions": -12.0,
    "col_transitions": -12.0,
}
UPPER_BOUNDS = {name: 0.0 for name in WEIGHT_NAMES}
UPPER_BOUNDS["lines_cleared"] = 20.0


def _clip(weights: dict[str, float]) -> dict[str, float]:
    return {
        name: min(UPPER_BOUNDS[name], max(LOWER_BOUNDS[name], float(weights[name])))
        for name in WEIGHT_NAMES
    }


def _seed_population(rng: random.Random, size: int) -> list[dict[str, float]]:
    population = [{name: float(DEFAULT_WEIGHTS[name]) for name in WEIGHT_NAMES}]
    while len(population) < size:
        candidate: dict[str, float] = {}
        for name in WEIGHT_NAMES:
            centre = DEFAULT_WEIGHTS[name]
            spread = max(0.08, (UPPER_BOUNDS[name] - LOWER_BOUNDS[name]) * 0.18)
            candidate[name] = rng.gauss(centre, spread)
        population.append(_clip(candidate))
    return population


def _candidate_worker(
    payload: tuple[dict[str, float], GAConfig],
) -> Metrics:
    weights, config = payload
    return evaluate_serial(
        weights,
        config.seed,
        config.games_per_candidate,
        name="candidate",
        backend=config.backend,
        max_pieces=config.max_pieces,
        engine_spec=config.engine_spec,
        policy_spec=config.policy_spec,
    )


def _select(
    population: list[dict[str, float]],
    scored: list[Metrics],
    rng: random.Random,
    tournament_size: int,
) -> dict[str, float]:
    contenders = rng.sample(list(zip(population, scored)), min(tournament_size, len(population)))
    parent, _ = max(contenders, key=lambda pair: pair[1].fitness)
    return dict(parent)


def _crossover(
    first: dict[str, float],
    second: dict[str, float],
    rng: random.Random,
) -> dict[str, float]:
    child: dict[str, float] = {}
    for index, name in enumerate(WEIGHT_NAMES):
        if index % 2 == 0:
            alpha = rng.random()
            value = alpha * first[name] + (1.0 - alpha) * second[name]
        else:
            value = first[name] if rng.random() < 0.5 else second[name]
        child[name] = value
    return child


def _mutate(candidate: dict[str, float], rng: random.Random, sigma: float) -> dict[str, float]:
    mutated = dict(candidate)
    for name in WEIGHT_NAMES:
        if rng.random() < 0.65:
            span = UPPER_BOUNDS[name] - LOWER_BOUNDS[name]
            mutated[name] += rng.gauss(0.0, sigma * span)
    # At least one gene changes, otherwise duplicate children waste evaluations.
    if mutated == candidate:
        name = rng.choice(WEIGHT_NAMES)
        span = UPPER_BOUNDS[name] - LOWER_BOUNDS[name]
        mutated[name] += rng.gauss(0.0, sigma * span)
    return _clip(mutated)


def _deduplicate(
    candidates: list[dict[str, float]],
    rng: random.Random,
) -> list[dict[str, float]]:
    unique: list[dict[str, float]] = []
    seen: set[tuple[float, ...]] = set()
    for candidate in candidates:
        key = tuple(round(candidate[name], 10) for name in WEIGHT_NAMES)
        if key not in seen:
            unique.append(candidate)
            seen.add(key)
    while len(unique) < len(candidates):
        unique.append(_mutate(rng.choice(unique), rng, 0.25))
    return unique


def evaluate_population(
    population: list[dict[str, float]],
    config: GAConfig,
) -> list[Metrics]:
    payloads = [(weights, config) for weights in population]
    if config.workers <= 1:
        return [_candidate_worker(payload) for payload in payloads]
    with ProcessPoolExecutor(max_workers=min(config.workers, len(payloads))) as executor:
        return list(executor.map(_candidate_worker, payloads))


def run_ga(
    config: GAConfig | None = None,
    *,
    progress: Callable[[GenerationRecord], None] | None = None,
    checkpoint_path: str | Path | None = None,
) -> GAResult:
    selected = config or GAConfig()
    selected.validate()
    rng = random.Random(selected.seed)
    population = _seed_population(rng, selected.population_size)
    history: list[GenerationRecord] = []
    best_weights = dict(DEFAULT_WEIGHTS)
    best_metrics: Metrics | None = None

    for generation in range(selected.generations):
        scored = evaluate_population(population, selected)
        order = sorted(
            range(len(population)),
            key=lambda index: (
                scored[index].fitness,
                scored[index].lines_mean,
                scored[index].weights["lines_cleared"],
            ),
            reverse=True,
        )
        leader_index = order[0]
        if best_metrics is None or scored[leader_index].fitness > best_metrics.fitness:
            best_metrics = scored[leader_index]
            best_weights = dict(population[leader_index])

        record = GenerationRecord(
            generation=generation + 1,
            best_fitness=scored[leader_index].fitness,
            mean_fitness=sum(metric.fitness for metric in scored) / len(scored),
            best_lines=scored[leader_index].lines_mean,
            best_weights=dict(population[leader_index]),
        )
        history.append(record)
        if progress:
            progress(record)

        if checkpoint_path:
            write_checkpoint(checkpoint_path, selected, history, best_weights)

        elites = [dict(population[index]) for index in order[: selected.elite_count]]
        children: list[dict[str, float]] = []
        while len(elites) + len(children) < selected.population_size:
            first = _select(population, scored, rng, selected.tournament_size)
            second = _select(population, scored, rng, selected.tournament_size)
            if rng.random() < selected.crossover_rate:
                child = _crossover(first, second, rng)
            else:
                child = dict(first)
            children.append(_mutate(child, rng, selected.mutation_sigma))
        population = _deduplicate(elites + children, rng)

    if best_metrics is None:
        raise RuntimeError("the GA completed without evaluating a candidate")
    return GAResult(
        best_weights=best_weights,
        best_metrics=best_metrics,
        history=history,
        config=selected,
    )


def write_checkpoint(
    path: str | Path,
    config: GAConfig,
    history: list[GenerationRecord],
    best_weights: dict[str, float],
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    data = {
        "config": asdict(config),
        "history": [asdict(record) for record in history],
        "best_weights": best_weights,
    }
    with temporary.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    temporary.replace(destination)
