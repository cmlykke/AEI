from __future__ import annotations

import time
from dataclasses import dataclass
from typing import FrozenSet, Optional, Tuple

from pyrimaa.board import Piece, Position

Steps = Tuple[Tuple[int, int], ...]


@dataclass(frozen=True)
class FilterLimits:
    """
    Non-time limits. Time is passed per call (time_budget_s or deadline).
    """
    max_attempts: int = 256
    fallback_to_unfiltered: bool = True


def _matches_constraints(
    from_pos: Position,
    steps: Steps,
    *,
    only_pieces: Optional[FrozenSet[int]] = None,
    only_squares: Optional[FrozenSet[int]] = None,
) -> bool:
    """
    Fast, slightly-approximate constraint check.

    only_pieces:
      Every moved piece (identified by piece at from-square in the ORIGINAL position)
      must be one of these piece codes.

    only_squares:
      Every step's from and to squares must be in this set of indices (0..63).
    """
    if only_pieces is None and only_squares is None:
        return True

    for from_ix, to_ix in steps:
        if only_squares is not None:
            if from_ix not in only_squares or to_ix not in only_squares:
                return False

        if only_pieces is not None:
            p = from_pos.piece_at(1 << from_ix)
            if p == Piece.EMPTY:
                return False
            if p not in only_pieces:
                return False

    return True


def get_filtered_move(
    pos: Position,
    *,
    time_budget_s: Optional[float] = None,
    deadline: Optional[float] = None,
    only_pieces: Optional[FrozenSet[int]] = None,
    only_squares: Optional[FrozenSet[int]] = None,
    limits: FilterLimits = FilterLimits(),
) -> tuple[Optional[Steps], Position]:
    """
    Find a legal move that matches given constraints within a time budget.

    You MUST pass exactly one of:
      - time_budget_s: seconds from now, OR
      - deadline: absolute time.perf_counter() deadline

    Returns (steps, result_position) like pos.get_rnd_step_move().
    If immobilized: returns (None, pos).

    Performance:
      - Does NOT call pos.get_moves().
      - Uses rejection sampling (sample random legal moves; accept if matches).
    """
    if (time_budget_s is None) == (deadline is None):
        raise ValueError("Pass exactly one of time_budget_s or deadline")

    if deadline is None:
        deadline = time.perf_counter() + max(0.0, float(time_budget_s))

    last_steps: Optional[Steps] = None
    last_result: Position = pos

    for _ in range(max(1, limits.max_attempts)):
        if time.perf_counter() >= deadline:
            break

        steps, result = pos.get_rnd_step_move()
        if steps is None:
            return None, pos

        last_steps, last_result = steps, result

        if _matches_constraints(
            pos,
            steps,
            only_pieces=only_pieces,
            only_squares=only_squares,
        ):
            return steps, result

    if limits.fallback_to_unfiltered and last_steps is not None:
        return last_steps, last_result

    return None, pos