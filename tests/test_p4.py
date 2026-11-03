from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from exp.ga import GAConfig, run_ga
from exp.metrics import DEFAULT_WEIGHTS
from exp.report import render_report
from exp.runner import evaluate


class RunnerTests(unittest.TestCase):
    def test_evaluation_is_deterministic(self) -> None:
        first = evaluate(DEFAULT_WEIGHTS, seed=17, n=2, backend="reference")
        second = evaluate(DEFAULT_WEIGHTS, seed=17, n=2, backend="reference")
        self.assertEqual(first.game_lines, second.game_lines)
        self.assertEqual(first.game_scores, second.game_scores)
        self.assertEqual(first.lines_mean, second.lines_mean)

    def test_parallel_and_serial_agree(self) -> None:
        serial = evaluate(DEFAULT_WEIGHTS, seed=5, n=2, backend="reference")
        parallel = evaluate(
            DEFAULT_WEIGHTS,
            seed=5,
            n=2,
            backend="reference",
            workers=2,
        )
        self.assertEqual(serial.game_lines, parallel.game_lines)
        self.assertEqual(serial.game_scores, parallel.game_scores)

    def test_public_metrics_contract(self) -> None:
        metrics = evaluate(DEFAULT_WEIGHTS, seed=9, n=1, backend="reference")
        payload = metrics.as_dict()
        self.assertEqual(payload["games"], 1)
        self.assertEqual(payload["average_lines"], metrics.lines_mean)
        self.assertIn("fitness", payload)
        self.assertEqual(metrics.backend, "reference")

    def test_rejects_invalid_game_count(self) -> None:
        with self.assertRaises(ValueError):
            evaluate(DEFAULT_WEIGHTS, seed=0, n=0)

    def test_external_engine_and_policy_path(self) -> None:
        metrics = evaluate(
            DEFAULT_WEIGHTS,
            seed=1,
            n=1,
            backend="external",
            engine_spec="tests.fake_backend:Engine",
            policy_spec="tests.fake_backend:policy",
        )
        self.assertEqual(metrics.backend, "external")
        self.assertEqual(metrics.game_lines, (1,))
        self.assertEqual(metrics.game_scores, (100,))


class GeneticAlgorithmTests(unittest.TestCase):
    def test_ga_smoke_and_artifacts(self) -> None:
        config = GAConfig(
            generations=2,
            population_size=5,
            games_per_candidate=1,
            seed=3,
            workers=1,
            max_pieces=20,
            backend="reference",
        )
        result = run_ga(config)
        self.assertEqual(len(result.history), 2)
        self.assertEqual(set(result.best_weights), set(DEFAULT_WEIGHTS))
        self.assertGreaterEqual(result.best_metrics.games, 1)

        baseline = evaluate(
            DEFAULT_WEIGHTS,
            seed=3,
            n=2,
            backend="reference",
            max_pieces=20,
        )
        tuned = evaluate(
            result.best_weights,
            seed=3,
            n=2,
            backend="reference",
            max_pieces=20,
        )
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            history = [
                {
                    "generation": record.generation,
                    "best_fitness": record.best_fitness,
                    "mean_fitness": record.mean_fitness,
                    "best_lines": record.best_lines,
                    "best_weights": record.best_weights,
                }
                for record in result.history
            ]
            report = render_report(
                output_dir=output,
                baseline=baseline,
                tuned=tuned,
                history=history,
                seed=3,
            )
            self.assertTrue(report.exists())
            for filename in (
                "fitness_curve.png",
                "metrics_comparison.png",
                "game_distribution.png",
                "weights_heatmap.png",
                "metrics.json",
                "games.csv",
                "history.csv",
            ):
                self.assertTrue((output / filename).exists(), filename)
            payload = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
            self.assertIn("baseline", payload)
            self.assertIn("tuned", payload)


if __name__ == "__main__":
    unittest.main()
