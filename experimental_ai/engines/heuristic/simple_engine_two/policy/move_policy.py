from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from pyrimaa.board import Position

from experimental_ai.common.search import PickerConfig, pick_move_anytime
from experimental_ai.utils.feature_extraction import (
    DEFAULT_WEIGHTS,
    EvalWeights,
    feature_frozen_pieces,
    feature_immediate_goal_threats,
    feature_material_counts,
    feature_mobility,
    feature_rabbit_advancement,
    feature_trap_control_and_danger,
    terminal_eval,
)
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
        t = terminal_eval(result_pos, perspective)
        if t is not None:
            return t

        w = config.weights
        s = 0.0

        # Select whichever heuristics this bot wants:
        s += w.material * feature_material_counts(result_pos, perspective)
        s += w.trap * feature_trap_control_and_danger(result_pos, perspective)
        s += w.frozen * feature_frozen_pieces(result_pos, perspective)
        s += w.mobility * feature_mobility(result_pos, perspective, use_legal_steps=config.legal_mobility)
        s += w.rabbits * feature_rabbit_advancement(result_pos, perspective)
        s += w.goal_threat * feature_immediate_goal_threats(result_pos, perspective)

        # Bot-specific shaping
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