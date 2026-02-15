## in Arimaa, the number of legal moves can go up to 200.000 in extreeme cases.
## for this reason, it is nessasary to rankorder the heuristics,
## so for most moves, only the least demanding tests gets called.

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Iterable, Optional, Sequence, Tuple

from pyrimaa.board import Position

from .feature_extraction import DEFAULT_WEIGHTS, EvalWeights, evaluate_position

Steps = Tuple[Tuple[int, int], ...]
MoveItem = Tuple[Position, Steps]  # (result_pos, steps)


@dataclass(frozen=True)
class TwoStageConfig:
    weights: EvalWeights = DEFAULT_WEIGHTS
    perspective: Optional[int] = None  # None => from_pos.color

    # Safety valves for very large branching factor
    max_stage1_moves: int = 50_000  # sample if more than this

    # Beam sizes
    stage1_top_k: int = 300         # keep this many after fast scoring
    stage2_top_k: int = 40          # re-score only this many with slow scoring

    # Control expensive feature usage
    stage1_legal_mobility: bool = False
    stage2_legal_mobility: bool = True

    # Tie-breaking / variety
    random_ties: bool = True
    rng_seed: Optional[int] = None


def _step_shaping_penalty(steps: Steps) -> float:
    """Tiny preference to use steps (avoid null-ish moves)."""
    return 0.01 * max(0, 4 - len(steps))


def score_position_fast(pos: Position, perspective: int, *, weights: EvalWeights) -> float:
    return evaluate_position(pos, perspective, weights=weights, legal_mobility=False)


def score_position_slow(pos: Position, perspective: int, *, weights: EvalWeights) -> float:
    return evaluate_position(pos, perspective, weights=weights, legal_mobility=True)


def select_best_move_two_stage(
    from_pos: Position,
    moves: Sequence[MoveItem],
    *,
    config: TwoStageConfig = TwoStageConfig(),
) -> tuple[Optional[Steps], Position]:
    """
    Pick best move from a provided move list [(result_pos, steps), ...].

    Returns (steps, result_pos) or (None, from_pos) if no moves.
    """
    if not moves:
        return None, from_pos

    perspective = from_pos.color if config.perspective is None else config.perspective
    rng = random.Random(config.rng_seed)

    # Stage 0: sample if absurdly many moves
    stage1_pool = list(moves)
    if config.max_stage1_moves > 0 and len(stage1_pool) > config.max_stage1_moves:
        stage1_pool = rng.sample(stage1_pool, k=config.max_stage1_moves)

    # Stage 1: fast scoring for many moves
    scored1: list[tuple[float, Position, Steps]] = []
    for result_pos, steps in stage1_pool:
        s = evaluate_position(
            result_pos,
            perspective,
            weights=config.weights,
            legal_mobility=config.stage1_legal_mobility,
        )
        s -= _step_shaping_penalty(steps)
        scored1.append((s, result_pos, steps))

    scored1.sort(key=lambda t: t[0], reverse=True)
    shortlist1 = scored1[: max(1, config.stage1_top_k)]
    shortlist2 = shortlist1[: max(1, config.stage2_top_k)]

    # Stage 2: slow scoring for top candidates only
    best_score = float("-inf")
    best: list[tuple[Steps, Position]] = []
    for _, result_pos, steps in shortlist2:
        s = evaluate_position(
            result_pos,
            perspective,
            weights=config.weights,
            legal_mobility=config.stage2_legal_mobility,
        )
        s -= _step_shaping_penalty(steps)

        if s > best_score:
            best_score = s
            best = [(steps, result_pos)]
        elif s == best_score:
            best.append((steps, result_pos))

    if not best:
        return None, from_pos

    if config.random_ties and len(best) > 1:
        return rng.choice(best)

    return best[0]




