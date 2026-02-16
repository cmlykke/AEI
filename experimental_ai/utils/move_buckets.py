"""
move_buckets.py

Defines “constraint buckets” for sampling moves.

A bucket is a lightweight filter (e.g., “only big pieces”, “only trap region squares”)
expressed as `MoveConstraints`. These are fed into `searchspace_reducer.get_filtered_move()`
to bias random move sampling toward more relevant areas without enumerating all moves.

This module should only contain:
- small, fast helpers to build constraint sets
- no scoring and no time/deadline loops (that’s `move_picker.py`)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Optional

from pyrimaa.board import (
    Color,
    Piece,
    Position,
    TRAP_C3_BIT,
    TRAP_F3_BIT,
    TRAP_C6_BIT,
    TRAP_F6_BIT,
    neighbors_of,
)


@dataclass(frozen=True)
class MoveConstraints:
    """Constraints passed to searchspace_reducer.get_filtered_move()."""
    only_pieces: Optional[FrozenSet[int]] = None
    only_squares: Optional[FrozenSet[int]] = None


def _bit_to_index(bit: int) -> int:
    return (bit.bit_length() - 1) if bit else 0


def _iter_bits(bits: int):
    """Yield single-bit masks for each set bit in a bitboard int."""
    while bits:
        b = bits & -bits
        bits ^= b
        yield b


def _trap_region_square_indices() -> FrozenSet[int]:
    """Trap squares + their adjacent squares."""
    sq: set[int] = set()
    for trap_bit in (TRAP_C3_BIT, TRAP_F3_BIT, TRAP_C6_BIT, TRAP_F6_BIT):
        sq.add(_bit_to_index(trap_bit))
        for n_bit in _iter_bits(neighbors_of(trap_bit)):
            sq.add(_bit_to_index(n_bit))
    return frozenset(sq)


def _goal_region_square_indices(side_to_move: int) -> FrozenSet[int]:
    """
    Squares near the opponent’s goal line.
    Gold attacks rank 8; Silver attacks rank 1.
    """
    if side_to_move == Color.GOLD:
        ranks = (6, 7)  # 7th/8th ranks
    else:
        ranks = (0, 1)  # 1st/2nd ranks
    return frozenset({r * 8 + f for r in ranks for f in range(8)})


def _big_pieces(side_to_move: int) -> FrozenSet[int]:
    """Bias toward higher-impact pieces for the side to move."""
    if side_to_move == Color.GOLD:
        return frozenset({Piece.GELEPHANT, Piece.GCAMEL, Piece.GHORSE})
    return frozenset({Piece.SELEPHANT, Piece.SCAMEL, Piece.SHORSE})


def build_constraint_buckets(pos: Position) -> list[MoveConstraints]:
    """
    Buckets are tried in a cycle by move_picker.
    Keep these few + cheap; sampling should stay fast.
    """
    return [
        MoveConstraints(),  # unfiltered (always include a catch-all)
        MoveConstraints(only_pieces=_big_pieces(pos.color)),
        MoveConstraints(only_squares=_trap_region_square_indices()),
        MoveConstraints(only_squares=_goal_region_square_indices(pos.color)),
    ]