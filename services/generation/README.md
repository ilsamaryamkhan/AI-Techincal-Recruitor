# Generation Service — Core AI #1  [ML]

Ingest company samples -> blueprint -> embed -> RAG-generate a fresh item -> call the oracle to verify the fault bites -> novelty filter -> store. LLM proposes; the oracle decides ground truth.

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

## Modules to build
- `app/pipeline.py` — ingest -> blueprint -> retrieve -> generate
- `app/oracle_client.py` — run verification methods; accept only if fault bites
- `app/novelty.py` — embedding similarity vs public samples (anti-leak)

Build against `/contracts`. Keep inputs/outputs matching the schemas there.
