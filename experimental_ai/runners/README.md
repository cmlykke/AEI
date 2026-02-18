# experimental_ai/runners

Optional helper scripts for local experimentation.

The canonical tournament runner/controller is still `pyrimaa.roundrobin`.
This folder is for convenience scripts you might write to:
- run a single engine locally
- run self-play batches
- wrap repeated evaluation workflows
- summarize results in `experimental_ai/artifacts/`

Keep runners small and focused; business logic should live in `experimental_ai/common/` or in the engine.
