"""
time_keeper.py

Small utility for managing per-move time budgets safely.

This module tracks an absolute `deadline` using a monotonic clock (`time.perf_counter()`),
and applies a configurable safety margin to reduce the risk of time forfeits.

It should remain minimal and generic: no move generation, no evaluation, no engine protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
import time


@dataclass
class TimeKeeper:
    """Tracks a per-move deadline using a monotonic clock."""
    safety_margin_s: float = 0.02  # keep a little buffer to avoid time forfeits
    _deadline: float | None = None

    @staticmethod
    def now() -> float:
        return time.perf_counter()

    def start_move(self, budget_s: float | None) -> None:
        if budget_s is None:
            self._deadline = None
        else:
            self._deadline = self.now() + max(0.0, budget_s - self.safety_margin_s)

    @property
    def deadline(self) -> float | None:
        return self._deadline

    def time_left(self) -> float | None:
        if self._deadline is None:
            return None
        return self._deadline - self.now()

    def out_of_time(self) -> bool:
        return self._deadline is not None and self.now() >= self._deadline