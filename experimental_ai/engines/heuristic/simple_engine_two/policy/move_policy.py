from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from pyrimaa.board import Position

from experimental_ai.common.search import PickerConfig, pick_move_anytime
from experimental_ai.utils.feature_extraction import DEFAULT_WEIGHTS, EvalWeights, evaluate_position
from experimental_ai.utils.move_buckets import build_constraint_buckets

Steps = Tuple[Tuple[int, int], ...]


@dataclass(frozen=True)
class MovePolicyConfig:
    weights: EvalWeights = DEFAULT_WEIGHTS
    perspective: Optional[int] = None  # None => pos.color
    legal_mobility: bool = False
    picker: PickerConfig = PickerConfig()


def pick_move(
    pos: Position,
    *,
    deadline: float | None,
    config: MovePolicyConfig = MovePolicyConfig(),
) -> tuple[Steps | None, Position]:
    """
    Engine policy entry point: builds buckets + scoring, delegates mechanics to common picker.
    """
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

    buckets = build_constraint_buckets(pos)
    return pick_move_anytime(
        pos,
        deadline=deadline,
        score_fn=score_fn,
        buckets=buckets,
        config=config.picker,
    )