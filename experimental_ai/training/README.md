# experimental_ai/training

Training code for ML-based experimental engines.

## What goes here
- Data generation pipelines (self-play, scraping, feature dumps)
- Dataset building/validation scripts
- Training loops, configs, checkpoints management
- Evaluation of trained models (offline metrics)

## Where trained outputs go
Put large generated artifacts under:
- `experimental_ai/artifacts/` (gitignored)
  - `models/` (checkpoints)
  - `datasets/`
  - `results/`

## Keep inference separate
Inference-time code that is needed to *run an engine* should live under:
- `experimental_ai/engines/ml/<engine_name>/`
so it can be launched by `roundrobin` via `cmdline = ...`.


