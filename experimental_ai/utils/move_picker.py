"""
move_picker.py

Deadline-aware (“anytime”) move picking.

This module is responsible for:
- spending a move budget safely: keep sampling candidate moves until `deadline`
- using constraint buckets (from `move_buckets.py`) + `searchspace_reducer.get_filtered_move()`
  to avoid full move enumeration (`pos.get_moves()`), which can be too slow under tight clocks
- scoring sampled moves via a provided `score_fn` and returning the best-so-far when time runs out

It should NOT implement the evaluation function itself; it receives scoring as a callback.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
import time
from typing import Callable, Optional, Tuple

from pyrimaa.board import Position

from .move_buckets import MoveConstraints, build_constraint_buckets
from .searchspace_reducer import FilterLimits, get_filtered_move

Steps = Tuple[Tuple[int, int], ...]
ScoreFn = Callable[[Position, Steps], float]  # (result_pos, steps) -> score


@dataclass(frozen=True)
class PickerConfig:
    """
    Controls sampling behavior.
    Time is controlled externally via `deadline`.
    """
    max_attempts_per_bucket: int = 96
    random_ties: bool = True
    rng_seed: int | None = None


def pick_move_anytime(
    pos: Position,
    *,
    deadline: float | None,
    score_fn: ScoreFn,
    config: PickerConfig = PickerConfig(),
    buckets: Optional[list[MoveConstraints]] = None,
) -> tuple[Optional[Steps], Position]:
    """
    Deadline-aware move picker.

    - If deadline is provided: cycles through constraint buckets and samples moves
      via searchspace_reducer.get_filtered_move(... deadline=deadline ...).
      Keeps the best-so-far until time is up.

    - If deadline is None: falls back to a single random legal move (fast + safe).
    """
    rng = random.Random(config.rng_seed)

    if deadline is None:
        steps, result = pos.get_rnd_step_move()
        if steps is None:
            return None, pos
        return steps, result

    if buckets is None:
        buckets = build_constraint_buckets(pos)

    best_score = float("-inf")
    best: list[tuple[Steps, Position]] = []

    bucket_i = 0
    while time.perf_counter() < deadline:
        c = buckets[bucket_i]
        bucket_i = (bucket_i + 1) % max(1, len(buckets))

        steps, result = get_filtered_move(
            pos,
            deadline=deadline,
            only_pieces=c.only_pieces,
            only_squares=c.only_squares,
            limits=FilterLimits(
                max_attempts=max(1, int(config.max_attempts_per_bucket)),
                fallback_to_unfiltered=True,
            ),
        )
        if steps is None:
            return None, pos  # immobilized

        s = score_fn(result, steps)
        if s > best_score:
            best_score = s
            best = [(steps, result)]
        elif s == best_score:
            best.append((steps, result))

        if time.perf_counter() >= deadline:
            break

    if not best:
        # Very defensive fallback: try to get *something* legal quickly.
        steps, result = get_filtered_move(
            pos,
            deadline=deadline,
            limits=FilterLimits(max_attempts=8, fallback_to_unfiltered=True),
        )
        if steps is None:
            return None, pos
        return steps, result

    if config.random_ties and len(best) > 1:
        return rng.choice(best)
    return best[0]