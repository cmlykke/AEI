"""
eval_glue.py

Public entry point for the bot logic in experimental_ai.utils.

This module wires together evaluation + move picking, but delegates heavy work to:
  - feature_extraction.py (position evaluation)
  - experimental_ai.common.search.anytime_picker (deadline-aware move selection)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from pyrimaa.board import Position

from experimental_ai.common.search import PickerConfig, pick_move_anytime
from .feature_extraction import DEFAULT_WEIGHTS, EvalWeights, evaluate_position
from .move_buckets import build_constraint_buckets

Steps = Tuple[Tuple[int, int], ...]


@dataclass(frozen=True)
class GlueConfig:
    """Configuration for the public move-selection entry point."""
    weights: EvalWeights = DEFAULT_WEIGHTS
    perspective: Optional[int] = None  # None => pos.color (side to move)

    legal_mobility: bool = False

    random_ties: bool = True
    rng_seed: Optional[int] = None

    max_attempts_per_bucket: int = 96


def get_eval_step_move(
    pos: Position,
    *,
    config: GlueConfig = GlueConfig(),
    deadline: float | None = None,
) -> tuple[Optional[Steps], Position]:
    perspective = pos.color if config.perspective is None else config.perspective

    def score_fn(result_pos: Position, steps: Steps) -> float:
        s = evaluate_position(
            result_pos,
            perspective,
            weights=config.weights,
            legal_mobility=config.legal_mobility,
        )
        s -= 0.01 * max(0, 4 - len(steps))
        return s

    picker_cfg = PickerConfig(
        max_attempts_per_bucket=config.max_attempts_per_bucket,
        random_ties=config.random_ties,
        rng_seed=config.rng_seed,
    )

    buckets = build_constraint_buckets(pos)
    return pick_move_anytime(
        pos,
        deadline=deadline,
        score_fn=score_fn,
        buckets=buckets,
        config=picker_cfg,
    )