# experimental_ai

This package is the home for *experimental* Arimaa AIs (both heuristic and ML) plus the tooling
needed to evaluate them.

The rest of the repo (`pyrimaa/`) provides the AEI protocol/controller and core game logic.
`experimental_ai/` is where we iterate quickly on engine ideas.

## How engines are run (current workflow)

Engines are typically launched as subprocesses by the AEI controller scripts, e.g.: