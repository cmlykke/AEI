"""
eval_glue.py

Public entry point for the bot logic in experimental_ai.utils.

Design rule:
- Outside code (engines, scripts, tests) should only need to call functions from this file.
- This module wires together evaluation + move picking, but delegates heavy work to:
  - feature_extraction.py (position evaluation)
  - move_picker.py (deadline-aware move selection)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from pyrimaa.board import Position

from .feature_extraction import DEFAULT_WEIGHTS, EvalWeights, evaluate_position
from .move_picker import PickerConfig, pick_move_anytime

Steps = Tuple[Tuple[int, int], ...]


@dataclass(frozen=True)
class GlueConfig:
    """Configuration for the public move-selection entry point."""
    weights: EvalWeights = DEFAULT_WEIGHTS
    perspective: Optional[int] = None  # None => pos.color (side to move)

    # Expensive evaluation toggle (keep False under tight time controls)
    legal_mobility: bool = False

    # Tie-breaking / variety
    random_ties: bool = True
    rng_seed: Optional[int] = None

    # Sampling controls (used by move_picker/searchspace_reducer)
    max_attempts_per_bucket: int = 96


def get_eval_step_move(
    pos: Position,
    *,
    config: GlueConfig = GlueConfig(),
    deadline: float | None = None,
) -> tuple[Optional[Steps], Position]:
    """
    Public move-selection entry point.

    Returns:
      (steps, result_position) like Position.get_rnd_step_move()
      If immobilized / no legal moves: (None, pos)

    Time behavior:
      - if `deadline` is provided (time.perf_counter() absolute time), this call is anytime:
        it returns the best move found so far when time runs out.
      - if `deadline` is None, it still returns a legal move quickly (via move_picker fallback).
    """
    perspective = pos.color if config.perspective is None else config.perspective

    def score_fn(result_pos: Position, steps: Steps) -> float:
        s = evaluate_position(
            result_pos,
            perspective,
            weights=config.weights,
            legal_mobility=config.legal_mobility,
        )
        # Tiny preference to use steps (avoid null-ish moves).
        s -= 0.01 * max(0, 4 - len(steps))
        return s

    picker_cfg = PickerConfig(
        max_attempts_per_bucket=config.max_attempts_per_bucket,
        random_ties=config.random_ties,
        rng_seed=config.rng_seed,
    )
    return pick_move_anytime(pos, deadline=deadline, score_fn=score_fn, config=picker_cfg)