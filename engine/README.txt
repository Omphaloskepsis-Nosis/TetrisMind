TetrisMind - Rule Engine
========================

Files:
  engine/board.py  Board, Piece, tetromino geometry, collision and line clears
  engine/srs.py    SRS clockwise/counter-clockwise rotation and wall kicks
  engine/game.py   Game loop, 7-bag, hold, T-Spin detection and scoring

Quick start (run from the TetrisMind_engine parent directory):
  from engine import Game

  game = Game(seed=42)
  game.move_left()
  game.rotate_cw()
  game.hard_drop()
  state = game.get_state()

AI-facing methods:
  game.apply_action("left" | "right" | "soft_drop" | "hard_drop" |
                    "rotate_cw" | "rotate_ccw" | "hold")
  game.get_state()
  game.legal_actions()

Scoring:
  Guideline-style line-clear/T-Spin base values, level multiplier,
  combo bonus and back-to-back bonus. Soft drop = 1 point/cell;
  hard drop = 2 points/cell.

Notes:
  - Coordinates use x-right/y-down.
  - The board is 10x20 by default; dimensions are configurable.
  - This is a deterministic rules engine, not a real-time keyboard frontend.
  - T-Spin uses the SRS three-corner test and fifth-kick mini upgrade.
