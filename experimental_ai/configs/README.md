# experimental_ai/configs

Configuration templates and reusable configs for experimental engines/runs.

## What goes here
- Config templates you want to reuse across machines
- Tournament configuration presets (time controls, bot lists, logging settings)

## What usually stays elsewhere
- Machine-specific/local configs (absolute paths, local-only bots):
  keep in `manual_testing/` (as you already do)

## Suggested structure (optional)
- `configs/tournaments/` – round-robin presets
- `configs/engines/` – per-engine option presets

## Tips
- Prefer **relative paths** in configs stored here so they work on any machine.
- Use **absolute paths** only in `manual_testing/` configs.



