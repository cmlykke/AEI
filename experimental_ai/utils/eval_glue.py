from __future__ import annotations

from dataclasses import dataclass
import random
import time
from typing import Optional, Tuple

from pyrimaa.board import Position

from .feature_extraction import DEFAULT_WEIGHTS, EvalWeights, score_move


Steps = Tuple[Tuple[int, int], ...]


@dataclass(frozen=True)
class GlueConfig:
    # Evaluation behavior
    weights: EvalWeights = DEFAULT_WEIGHTS
    perspective: Optional[int] = None  # None => pos.color (side to move)

    # Performance: legal mobility is the expensive part in your current evaluator.
    # For move-picking, you usually want this False until you add top-K refinement.
    legal_mobility: bool = False

    # Tie-breaking / variety
    random_ties: bool = True
    rng_seed: Optional[int] = None


def get_eval_step_move(
    pos: Position,
    *,
    config: GlueConfig = GlueConfig(),
    deadline: float | None = None,
) -> tuple[Optional[Steps], Position]:
    """
    Replacement for: steps, result = pos.get_rnd_step_move()

    Returns:
      (steps, result_position) like get_rnd_step_move().
      If immobilized / no legal moves: (None, pos)

    Strategy:
      - enumerate full moves: pos.get_moves() -> {result_pos: steps}
      - score each result_pos using feature_extraction.score_move(...)
      - pick argmax

    If deadline is provided, returns the best move found so far when time runs out.
    """
    moves = pos.get_moves()
    if not moves:
        return None, pos

    perspective = pos.color if config.perspective is None else config.perspective
    rng = random.Random(config.rng_seed)

    best_score = float("-inf")
    best: list[tuple[Steps, Position]] = []

    # Note: moves is {Position: Steps}
    for result_pos, steps in moves.items():
        if deadline is not None and time.perf_counter() >= deadline:
            break

        s = score_move(
            pos,
            result_pos,
            steps,
            perspective=perspective,
            weights=config.weights,
        )

        # If you later wire legal_mobility through, do it inside feature_extraction.evaluate_position().
        # For now, GlueConfig.legal_mobility is kept for forward compatibility.

        if s > best_score:
            best_score = s
            best = [(steps, result_pos)]
        elif s == best_score:
            best.append((steps, result_pos))

        # If a single score computation ran long, don't start another one.
        if deadline is not None and time.perf_counter() >= deadline:
            break

    if not best:
        # Deterministic fallback: just pick the first item from a list snapshot.
        result_pos, steps = list(moves.items())[0]
        return steps, result_pos

    if config.random_ties and len(best) > 1:
        steps, result = rng.choice(best)
    else:
        steps, result = best[0]

    return steps, result