from __future__ import annotations

import unittest

from ai.policy import DEFAULT_WEIGHTS as AI_WEIGHTS
from ai.policy import policy
from contracts import Action, Engine
from engine import Game
from exp.metrics import DEFAULT_WEIGHTS
from exp.runner import evaluate


class RuleEngineTests(unittest.TestCase):
    def test_engine_supports_movement_rotation_and_lock(self) -> None:
        game = Game(seed=7)
        before = game.get_state()
        self.assertTrue(game.rotate_cw())
        game.move_left()
        distance = game.hard_drop()
        after = game.get_state()
        self.assertGreaterEqual(distance, 0)
        self.assertGreater(after["score"], before["score"])
        self.assertNotEqual(after["current"], before["current"])

    def test_adapter_returns_numeric_render_state(self) -> None:
        engine = Engine(seed=42)
        state = engine.reset()
        self.assertEqual(len(state.board), 20)
        self.assertEqual(len(state.board[0]), 10)
        self.assertTrue(state.current_cells)
        self.assertIsInstance(state.current_kind, int)
        self.assertNotEqual(state.current_kind, 0)


class AIPolicyTests(unittest.TestCase):
    def test_policy_returns_contract_actions_and_places_piece(self) -> None:
        engine = Engine(seed=42)
        state = engine.reset()
        action = policy(state, AI_WEIGHTS, time_limit_ms=12.0)
        self.assertIsInstance(action, Action)
        placed = engine.auto_step(AI_WEIGHTS, time_limit_ms=12.0)
        self.assertGreaterEqual(placed.piece_count, 1)
        self.assertTrue(any(cell for row in placed.board for cell in row))

    def test_ga_weights_are_shared_with_p3(self) -> None:
        self.assertEqual(set(DEFAULT_WEIGHTS), set(AI_WEIGHTS))


class FullPipelineTests(unittest.TestCase):
    def test_auto_backend_uses_real_engine(self) -> None:
        metrics = evaluate(
            DEFAULT_WEIGHTS,
            seed=42,
            n=1,
            backend="auto",
            max_pieces=8,
        )
        self.assertEqual(metrics.backend, "external")
        self.assertEqual(len(metrics.game_lines), 1)
        self.assertGreater(metrics.pieces_mean, 0)


if __name__ == "__main__":
    unittest.main()
