
"""
experimental_ai.utils

Internal utility package for the experimental bot.

Public API policy:
- External code should import ONLY from experimental_ai.utils.eval_glue
  (or from this package, which re-exports the same glue functions).
- Other modules in this folder are considered internal implementation details.
"""

from .eval_glue import GlueConfig, get_eval_step_move

__all__ = ["GlueConfig", "get_eval_step_move"]