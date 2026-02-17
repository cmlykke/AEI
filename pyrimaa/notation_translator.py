from __future__ import annotations

import re
from typing import Iterable, List


_INTERNAL_HEADER_RE = re.compile(r"^\s*(?P<num>\d+)\s*(?P<side>[gGsS])(?:\s+(?P<rest>.*))?\s*$")


class NotationTranslationError(ValueError):
    """Raised when a move line cannot be translated between notations."""


def internal_side_to_db_side(side: str) -> str:
    """
    Convert the project's internal side letters to the database side letters.

    Internal: 'g' (Gold), 's' (Silver)
    Database: 'w' (White/Gold), 'b' (Black/Silver)
    """
    if not side or len(side) != 1:
        raise NotationTranslationError(f"Invalid side: {side!r}")
    side_l = side.lower()
    if side_l == "g":
        return "w"
    if side_l == "s":
        return "b"
    raise NotationTranslationError(f"Unsupported internal side: {side!r}")


def translate_move_line_internal_to_db(line: str) -> str:
    """
    Translate a single move line from the project's internal notation into the
    database format described by the user.

    Example:
      "9s de6w Re5n Re6e Rf6x de7s" -> "9b de6w Re5n Re6e Rf6x de7s"
      "1g Ra1 Rb1 ... Rh2"         -> "1w Ra1 Rb1 ... Rh2"

    Notes:
    - This function only changes the move header side letter (g/s -> w/b).
    - The step/placement tokens are preserved verbatim.
    - Whitespace is normalized to: "<num><side> <rest>" (or "<num><side>" if no rest).
    """
    if line is None:
        raise NotationTranslationError("Line is None")

    m = _INTERNAL_HEADER_RE.match(line)
    if not m:
        raise NotationTranslationError(
            f"Line does not look like an internal move line '<num><g|s> ...': {line!r}"
        )

    num = m.group("num")
    side = m.group("side")
    rest = m.group("rest") or ""

    db_side = internal_side_to_db_side(side)

    # Normalize *internal* whitespace within the move (so multiple spaces don't survive)
    rest = " ".join(rest.split())

    if rest:
        return f"{num}{db_side} {rest}"
    return f"{num}{db_side}"


def translate_game_lines_internal_to_db(lines: Iterable[str]) -> List[str]:
    """
    Translate an iterable of internal move lines to database move lines.
    """
    return [translate_move_line_internal_to_db(line) for line in lines]


def translate_game_string_internal_to_db(game: str) -> str:
    """
    Translate a whole game string (newline-separated internal move lines)
    to the database format (newline-separated with w/b headers).

    Blank/whitespace-only lines are ignored.
    """
    if game is None:
        raise NotationTranslationError("Game is None")
    raw_lines = game.splitlines()
    out: List[str] = []
    for line in raw_lines:
        if not line.strip():
            continue
        out.append(translate_move_line_internal_to_db(line))
    return "\n".join(out)