# Deep Research Evals

This directory contains the MVP evaluation pipeline for the Deep Research agent.

## What It Covers

- `single-step`: unit-like checks for scoping, research tool choice, verification, and report structure
- `full-turn`: end-to-end workflow checks over one complete research request
- `multi-turn`: thread continuity checks over two turns with the same `thread_id`

## Design Notes

- Tests run through the public graph entrypoints instead of patching core business logic.
- `mocked` mode monkeypatches `tavily_search` with deterministic fixture responses.
- `live` mode keeps the real Tavily + model stack.
- LangSmith tracing is optional. If `.env` contains `LANGSMITH_TRACING=true`, traces are emitted automatically. Custom evaluator scores are also pushed as feedback when possible.

## Usage

Run the default mocked suite:

```bash
uv run python scripts/run_evals.py
```

Run only smoke:

```bash
uv run pytest evals/smoke -q
```

Run a live full-turn subset:

```bash
uv run python scripts/run_evals.py --mode live --category full_turn -m live_model
```

## Environment

The test suite loads `.env` automatically. Optional knobs:

- `EVAL_MODE=mocked|live`
- `EVAL_ENABLE_JUDGE=true|false`
- `LANGSMITH_PROJECT=deep-research-evals`

## Current Tradeoffs

- The report judge is opt-in and uses the configured OpenAI-compatible model.
- The skill-sensitive full-turn case auto-skips when no local domain skill directories exist.
- `auto_reject` currently validates that execution stops before approval is resumed, which is enough to assert that no search budget is consumed.

