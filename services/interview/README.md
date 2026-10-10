# Interview Service — session orchestrator  [Ilsa]

Agentic stateful policy for the comprehension interview: present artifact -> ask -> listen (ASR) -> score (calls scoring) -> adapt follow-up from the candidate's own claims.

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8004
```

## Modules to build
- `app/orchestrator.py` — present -> ask -> listen -> score -> adapt loop
- `app/asr.py` — faster-whisper transcription
- `app/followup.py` — generate next question from a candidate claim

Build against `/contracts`. Keep inputs/outputs matching the schemas there.
