# experimental_ai/commo

Shared, engine-agnostic building blocks used by multiple experimental engines.

## What goes here
- Feature extraction / representations shared across engines
- Search infrastructure (e.g., generic minimax/MCTS scaffolding)
- Evaluation helpers / metrics / selectors
- Time-control helpers and other “mechanics”

## What should NOT go here
- Engine-specific heuristics/weights/tuning knobs → keep inside that engine under `experimental_ai/engines/...`

## Notes
If a module in `experimental_ai/utils/` becomes stable and reused by 2+ engines, consider moving it here
into a clearer subpackage (e.g. `common/features`, `common/eval`, `common/time`).
