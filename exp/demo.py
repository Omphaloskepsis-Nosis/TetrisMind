"""Standalone P4 entry: ``python -m exp.demo``."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

from exp.ga import GAConfig, GenerationRecord, run_ga
from exp.metrics import DEFAULT_WEIGHTS
from exp.report import render_report
from exp.runner import evaluate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m exp.demo",
        description="TetrisMind P4 GA tuning and report demo",
    )
    parser.add_argument("--generations", type=int, default=30)
    parser.add_argument("--population", type=int, default=16)
    parser.add_argument("--games", type=int, default=2, help="games per candidate")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--max-pieces", type=int, default=80)
    parser.add_argument(
        "--backend",
        choices=("auto", "external", "reference"),
        default="auto",
    )
    parser.add_argument("--engine", default="contracts:Engine")
    parser.add_argument("--policy", default="ai.policy:policy")
    parser.add_argument("--output", type=Path, default=Path("artifacts/p4_demo"))
    return parser


def _print_progress(record: GenerationRecord) -> None:
    print(
        f"[GA {record.generation:02d}] best={record.best_fitness:.3f} "
        f"mean={record.mean_fitness:.3f} lines={record.best_lines:.2f}",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = GAConfig(
        generations=args.generations,
        population_size=args.population,
        games_per_candidate=args.games,
        seed=args.seed,
        workers=args.workers,
        max_pieces=args.max_pieces,
        backend=args.backend,
        engine_spec=args.engine,
        policy_spec=args.policy,
    )
    config.validate()
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[P4] output={output_dir}")
    print("[P4] evaluating default weights...", flush=True)
    baseline = evaluate(
        DEFAULT_WEIGHTS,
        seed=config.seed,
        n=max(config.games_per_candidate, 2),
        name="baseline",
        backend=config.backend,
        workers=config.workers,
        max_pieces=config.max_pieces,
        engine_spec=config.engine_spec,
        policy_spec=config.policy_spec,
    )
    print(
        f"[P4] baseline lines={baseline.lines_mean:.2f} "
        f"score={baseline.score_mean:.1f} backend={baseline.backend}",
        flush=True,
    )

    result = run_ga(
        config,
        progress=_print_progress,
        checkpoint_path=output_dir / "checkpoint.json",
    )
    # Re-evaluate the winner on the full report sample. GA candidates use a
    # smaller sample to keep the search affordable.
    tuned = evaluate(
        result.best_weights,
        seed=config.seed,
        n=baseline.games,
        name="tuned",
        backend=config.backend,
        workers=config.workers,
        max_pieces=config.max_pieces,
        engine_spec=config.engine_spec,
        policy_spec=config.policy_spec,
    )
    history = [asdict(record) for record in result.history]
    report_path = render_report(
        output_dir=output_dir,
        baseline=baseline,
        tuned=tuned,
        history=history,
        seed=config.seed,
    )
    (output_dir / "best_weights.json").write_text(
        json.dumps(
            {
                "seed": config.seed,
                "backend": tuned.backend,
                "weights": result.best_weights,
                "metrics": tuned.as_dict(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / "run_config.json").write_text(
        json.dumps(
            {"config": asdict(config), "purpose": "TetrisMind P4 reproducibility"},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    improvement = tuned.lines_mean - baseline.lines_mean
    print(
        f"[P4] tuned lines={tuned.lines_mean:.2f} ({improvement:+.2f}) "
        f"score={tuned.score_mean:.1f}",
        flush=True,
    )
    print(f"[P4] report={report_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
