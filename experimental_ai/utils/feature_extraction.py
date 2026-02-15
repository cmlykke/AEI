from __future__ import annotations

"""
feature_extraction.py

Position evaluation and feature engineering.

This module is responsible for:
- extracting fast, mostly-local heuristic features from a `pyrimaa.board.Position`
- combining those features into a scalar evaluation (“good for perspective”)
- optionally exposing both cheap and expensive variants (e.g., legal-mobility on/off)

It should NOT manage time controls or pick moves.
"""

"""
Basic (fast-ish) feature extraction + move scoring for Arimaa positions.

Design goals:
- Works directly with `pyrimaa.board.Position` objects returned by `Position.get_moves()`
- Each feature is implemented as its own function (as requested)
- A simple linear evaluator combines features into a single move score

Conventions:
- `perspective` is the side we are scoring for (Color.GOLD or Color.SILVER).
- Returned scores are "good for perspective": higher is better for that side.

This is intentionally a *first pass* evaluator: it is heuristic and approximate.
You can later tune weights, add phase scaling, and cache expensive computations.
"""


from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Tuple

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

# --- Utilities ----------------------------------------------------------------


def _popcount(x: int) -> int:
    return int(x).bit_count()


def _iter_bits(bits: int) -> Iterable[int]:
    """Yield single-bit masks from a bitboard."""
    while bits:
        b = bits & -bits
        bits ^= b
        yield b


def _rank_of_index(ix: int) -> int:
    """0..7 (rank1..rank8) where 0 is rank1 (bottom in the long-board print)."""
    return ix // 8


def _file_of_index(ix: int) -> int:
    return ix % 8


def _bit_to_index(bit: int) -> int:
    # Small local helper (pyrimaa.board has bit_to_index too, but not imported here).
    # This simple loop is fine at this scale (64 max).
    return (bit.bit_length() - 1) if bit else 0


def _piece_value_by_rank(piece_rank: int) -> int:
    """
    Hand-tuned, "classic" material weights.
    These are not gospel—just reasonable starting numbers.
    """
    return {
        Piece.GRABBIT: 1,
        Piece.GCAT: 2,
        Piece.GDOG: 3,
        Piece.GHORSE: 5,
        Piece.GCAMEL: 9,
        Piece.GELEPHANT: 14,
    }.get(piece_rank, 0)


def _all_pieces_bitboard(pos: Position) -> int:
    return pos.placement[Color.GOLD] | pos.placement[Color.SILVER]


def _goal_rank_for(color: int) -> int:
    # Gold promotes on rank 8 (index rank 7), Silver on rank 1 (index rank 0)
    return 7 if color == Color.GOLD else 0


# --- Feature 1: material counts by piece type ---------------------------------


def feature_material_counts(pos: Position, perspective: int) -> float:
    """
    Material (by piece type) for perspective minus opponent.

    Uses simple piece values * counts.
    """
    gold = 0
    silver = 0

    # Gold pieces
    for p in (Piece.GRABBIT, Piece.GCAT, Piece.GDOG, Piece.GHORSE, Piece.GCAMEL, Piece.GELEPHANT):
        gold += _piece_value_by_rank(p) * _popcount(pos.bitBoards[p])

    # Silver pieces
    for p in (Piece.SRABBIT, Piece.SCAT, Piece.SDOG, Piece.SHORSE, Piece.SCAMEL, Piece.SELEPHANT):
        silver += _piece_value_by_rank(p & Piece.DECOLOR) * _popcount(pos.bitBoards[p])

    score_for_gold = float(gold - silver)
    return score_for_gold if perspective == Color.GOLD else -score_for_gold


# --- Feature 2: trap control / trap danger ------------------------------------


_TRAP_BITS = (TRAP_C3_BIT, TRAP_F3_BIT, TRAP_C6_BIT, TRAP_F6_BIT)


def _trap_defenders(pos: Position, trap_bit: int, color: int) -> int:
    """Number of same-color adjacent defenders to a trap square."""
    return _popcount(neighbors_of(trap_bit) & pos.placement[color])


def _trap_attackers(pos: Position, trap_bit: int, color: int) -> int:
    """Number of enemy adjacent pieces to a trap square (rough attacking presence)."""
    return _popcount(neighbors_of(trap_bit) & pos.placement[color ^ 1])


def feature_trap_control_and_danger(pos: Position, perspective: int) -> float:
    """
    Produces a single scalar combining:
    - trap control: defenders - attackers around each trap
    - trap danger: penalty for having pieces on/adjacent to trap that are under-defended

    Notes:
    - In this codebase, *captured-by-trap* pieces are removed during move generation.
      So "piece sitting undefended on a trap" should usually not exist in stable positions,
      but can still matter in partial-step positions; we score it anyway.
    """
    score_for_gold = 0.0

    for trap in _TRAP_BITS:
        g_def = _trap_defenders(pos, trap, Color.GOLD)
        s_def = _trap_defenders(pos, trap, Color.SILVER)
        g_att = _trap_attackers(pos, trap, Color.GOLD)
        s_att = _trap_attackers(pos, trap, Color.SILVER)

        # Control: defenders minus attackers (lightweight, symmetric)
        score_for_gold += 0.35 * ((g_def - g_att) - (s_def - s_att))

        # Danger: adjacent pieces with low support are "hanging" near the trap
        # We approximate: if you have pieces adjacent and defenders are low, penalize.
        g_adj = _popcount(neighbors_of(trap) & pos.placement[Color.GOLD])
        s_adj = _popcount(neighbors_of(trap) & pos.placement[Color.SILVER])

        # Under-defended adjacency penalty (the 2 is arbitrary and tunable)
        score_for_gold -= 0.50 * max(0, g_adj - 2 * g_def)
        score_for_gold += 0.50 * max(0, s_adj - 2 * s_def)

        # Extra penalty if a piece is actually on the trap square and defended poorly
        if pos.placement[Color.GOLD] & trap:
            score_for_gold -= 1.25 * max(0, 1 - g_def)
        if pos.placement[Color.SILVER] & trap:
            score_for_gold += 1.25 * max(0, 1 - s_def)

    return score_for_gold if perspective == Color.GOLD else -score_for_gold


# --- Feature 3: frozen pieces count / important frozen pieces ------------------


_IMPORTANT_RANK_MULT = {
    Piece.GRABBIT: 0.6,
    Piece.GCAT: 1.0,
    Piece.GDOG: 1.0,
    Piece.GHORSE: 1.6,
    Piece.GCAMEL: 2.0,
    Piece.GELEPHANT: 2.5,
}


def _frozen_weight_sum(pos: Position, color: int) -> float:
    """Sum of weighted frozen pieces for a given color."""
    total = 0.0
    pcbit = color << 3

    for rank in (Piece.GRABBIT, Piece.GCAT, Piece.GDOG, Piece.GHORSE, Piece.GCAMEL, Piece.GELEPHANT):
        piece = rank | pcbit
        bits = pos.bitBoards[piece]
        if not bits:
            continue
        mult = _IMPORTANT_RANK_MULT.get(rank, 1.0)
        for b in _iter_bits(bits):
            if pos.is_frozen_at(b):
                total += mult
    return total


def feature_frozen_pieces(pos: Position, perspective: int) -> float:
    """
    Penalize frozen pieces for perspective (and reward opponent frozen pieces).
    Weighted so freezing elephants/camels/horses matters more than rabbits.
    """
    g = _frozen_weight_sum(pos, Color.GOLD)
    s = _frozen_weight_sum(pos, Color.SILVER)
    score_for_gold = (s - g)  # more frozen silver is good for gold
    return score_for_gold if perspective == Color.GOLD else -score_for_gold


# --- Feature 4: mobility (legal steps, or approximate mobility) ----------------


def feature_mobility(pos: Position, perspective: int, use_legal_steps: bool = True) -> float:
    """
    Mobility heuristic.

    If use_legal_steps=True:
      mobility = (number of legal steps for gold) - (number of legal steps for silver),
      computed via temporarily scoring a null-turn position for each side.
      This is more expensive but aligns with actual rules (freeze, rabbits back, pushes).

    If use_legal_steps=False:
      approximate mobility = empty-adjacencies for each side (ignores many rules),
      cheaper but noisier.

    Either way, returns "good for perspective".
    """
    if use_legal_steps:
        # We need "step count if X were to move".
        # Easiest: create a shallow Position with same boards but different `color`.
        gpos = Position(Color.GOLD, pos.stepsLeft, pos.bitBoards, placement=pos.placement, zobrist=pos._zhash)
        spos = Position(Color.SILVER, pos.stepsLeft, pos.bitBoards, placement=pos.placement, zobrist=pos._zhash)

        g_steps = len(gpos.get_steps())
        s_steps = len(spos.get_steps())
        score_for_gold = float(g_steps - s_steps)
        return score_for_gold if perspective == Color.GOLD else -score_for_gold

    # Approximate: count empty neighbors of own pieces (very rough)
    empty = pos.bitBoards[Piece.EMPTY]
    g_mob = _popcount(neighbors_of(pos.placement[Color.GOLD]) & empty)
    s_mob = _popcount(neighbors_of(pos.placement[Color.SILVER]) & empty)
    score_for_gold = float(g_mob - s_mob)
    return score_for_gold if perspective == Color.GOLD else -score_for_gold


# --- Feature 5: rabbit advancement / goal progress -----------------------------


def _rabbit_advancement_sum(pos: Position, color: int) -> float:
    """
    Sum of rabbit progress toward goal (bigger is better for that color).

    Gold rabbits want higher ranks; silver rabbits want lower ranks.
    """
    rabbit_piece = Piece.GRABBIT if color == Color.GOLD else Piece.SRABBIT
    bits = pos.bitBoards[rabbit_piece]
    if not bits:
        return 0.0

    total = 0.0
    for b in _iter_bits(bits):
        ix = _bit_to_index(b)
        r = _rank_of_index(ix)
        prog = r if color == Color.GOLD else (7 - r)
        total += prog
    return total


def feature_rabbit_advancement(pos: Position, perspective: int) -> float:
    """
    Net rabbit progress: my rabbits advanced minus opponent rabbits advanced.
    """
    g = _rabbit_advancement_sum(pos, Color.GOLD)
    s = _rabbit_advancement_sum(pos, Color.SILVER)
    score_for_gold = float(g - s)
    return score_for_gold if perspective == Color.GOLD else -score_for_gold


# --- Feature 6: immediate goal threats (near-promotion patterns) ---------------


def _count_near_goal_threats(pos: Position, color: int) -> int:
    """
    Very simple "goal threat" detector:
    - rabbits on the 7th rank (for gold) / 2nd rank (for silver)
    - with at least one forward square empty
    - and (optionally) not frozen (we check that)

    This does not prove a forced goal; it’s a fast heuristic signal.
    """
    rabbit_piece = Piece.GRABBIT if color == Color.GOLD else Piece.SRABBIT
    rabbits = pos.bitBoards[rabbit_piece]
    if not rabbits:
        return 0

    threats = 0
    empty = pos.bitBoards[Piece.EMPTY]
    forward_delta = 8 if color == Color.GOLD else -8

    target_rank = 6 if color == Color.GOLD else 1  # one step from goal rank
    for b in _iter_bits(rabbits):
        ix = _bit_to_index(b)
        if _rank_of_index(ix) != target_rank:
            continue
        if pos.is_frozen_at(b):
            continue
        fwd_ix = ix + forward_delta
        if 0 <= fwd_ix < 64:
            if empty & (1 << fwd_ix):
                threats += 1
    return threats


def feature_immediate_goal_threats(pos: Position, perspective: int) -> float:
    """
    Count near-goal rabbit threats for each side, return net for perspective.
    """
    g = _count_near_goal_threats(pos, Color.GOLD)
    s = _count_near_goal_threats(pos, Color.SILVER)
    score_for_gold = float(g - s)
    return score_for_gold if perspective == Color.GOLD else -score_for_gold


# --- Combining features into a move score -------------------------------------


@dataclass(frozen=True)
class EvalWeights:
    material: float = 1.00
    trap: float = 1.30
    frozen: float = 0.90
    mobility: float = 0.08
    rabbits: float = 0.12
    goal_threat: float = 1.75


DEFAULT_WEIGHTS = EvalWeights()


def evaluate_position(
    pos: Position,
    perspective: int,
    *,
    weights: EvalWeights = DEFAULT_WEIGHTS,
    legal_mobility: bool = True,
) -> float:
    """
    Linear evaluation function.

    Includes terminal checks:
    - end state from pos.is_end_state(): +inf win, -inf loss (from perspective)
    """
    end = pos.is_end_state()
    if end:
        # `is_end_state()` uses absolute winner:
        #   +1 => GOLD wins, -1 => SILVER wins
        winner_color = Color.GOLD if end == 1 else Color.SILVER
        return float("inf") if winner_color == perspective else float("-inf")

    score = 0.0
    score += weights.material * feature_material_counts(pos, perspective)
    score += weights.trap * feature_trap_control_and_danger(pos, perspective)
    score += weights.frozen * feature_frozen_pieces(pos, perspective)
    score += weights.mobility * feature_mobility(pos, perspective, use_legal_steps=legal_mobility)
    score += weights.rabbits * feature_rabbit_advancement(pos, perspective)
    score += weights.goal_threat * feature_immediate_goal_threats(pos, perspective)
    return score


def score_move(
    from_pos: Position,
    to_pos: Position,
    steps: Tuple[Tuple[int, int], ...] | None = None,
    *,
    perspective: int | None = None,
    weights: EvalWeights = DEFAULT_WEIGHTS,
) -> float:
    """
    Score a candidate move result (`to_pos`) originating from `from_pos`.

    Typically:
        moves = pos.get_moves()  # {Position: steps}
        for result_pos, steps in moves.items():
            s = score_move(pos, result_pos, steps)

    The scoring is "good for the mover" by default (perspective = from_pos.color).
    """
    if perspective is None:
        perspective = from_pos.color

    # Basic approach: evaluate resulting position from the mover's perspective.
    base = evaluate_position(to_pos, perspective, weights=weights)

    # Small shaping: prefer using more steps if it improves evaluation?
    # For now: a tiny penalty for "wasting" steps (null-ish moves), but not too strong.
    # (steps is a tuple of (from_ix, to_ix) pairs; can be empty.)
    if steps is not None:
        base -= 0.01 * max(0, 4 - len(steps))

    return base


def score_all_moves(
    pos: Position,
    *,
    weights: EvalWeights = DEFAULT_WEIGHTS,
    perspective: int | None = None,
) -> Dict[Position, float]:
    """
    Convenience helper: generate moves and return {result_position: score}.
    """
    if perspective is None:
        perspective = pos.color

    moves: Mapping[Position, Tuple[Tuple[int, int], ...]] = pos.get_moves()
    scored: Dict[Position, float] = {}
    for result_pos, steps in moves.items():
        scored[result_pos] = score_move(pos, result_pos, steps, perspective=perspective, weights=weights)
    return scored