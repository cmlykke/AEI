from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Optional


@dataclass(frozen=True)
class MoveConstraints:
    """Constraints passed to common.search.sampling.get_filtered_move()."""
    only_pieces: Optional[FrozenSet[int]] = None
    only_squares: Optional[FrozenSet[int]] = None