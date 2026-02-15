
"""
eval_glue.py

Thin integration layer (“glue”) between the AEI engine loop and the bot’s move-selection code.

This module should:
- expose a simple, stable entry point like `get_eval_step_move(pos, deadline=...)`
- translate engine concerns (time/deadline, perspective) into calls to lower-level utilities
- avoid heavy logic: move sampling, bucket selection, and search live in other modules
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from pyrimaa.board import Color, Position

from .feature_extraction import DEFAULT_WEIGHTS, EvalWeights, evaluate_position
from .move_picker import PickerConfig, pick_move_anytime

Steps = Tuple[Tuple[int, int], ...]


@dataclass(frozen=True)
class GlueConfig:
    # Evaluation behavior
    weights: EvalWeights = DEFAULT_WEIGHTS
    perspective: Optional[int] = None  # None => pos.color (side to move)

    # Performance: legal mobility is expensive; keep False under time pressure
    legal_mobility: bool = False

    # Tie-breaking / variety
    random_ties: bool = True
    rng_seed: Optional[int] = None

    # Search-space reducer controls
    max_attempts_per_bucket: int = 96


def get_eval_step_move(
    pos: Position,
    *,
    config: GlueConfig = GlueConfig(),
    deadline: float | None = None,
) -> tuple[Optional[Steps], Position]:
    """
    Thin entry point used by the AEI engine.
    Delegates the timed move sampling to move_picker.
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