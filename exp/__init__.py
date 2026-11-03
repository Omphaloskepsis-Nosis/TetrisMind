"""TetrisMind P4: reproducible experiments and genetic weight tuning."""

from exp.metrics import DEFAULT_WEIGHTS, Metrics
from exp.runner import evaluate

__all__ = ["DEFAULT_WEIGHTS", "Metrics", "evaluate"]
