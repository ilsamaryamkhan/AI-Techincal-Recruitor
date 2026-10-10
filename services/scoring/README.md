# Scoring Service — Core AI #2 brain  [ML]

Score a candidate's spoken/written explanation against an item's expected_observations: AST/static grounding, NLI entailment per observation, and fluent-wrongness detection (claims cross-checked against ground truth).

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
```

## Modules to build
- `app/grounding.py` — tree-sitter AST + static facts (complexity, patterns)
- `app/nli.py` — DeBERTa-v3-NLI: does the explanation entail each observation?
- `app/fluent_wrongness.py` — flag claims that contradict the grounded truth

Build against `/contracts`. Keep inputs/outputs matching the schemas there.
