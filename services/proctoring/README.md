# Proctoring Service — Core AI #3  [CV]

OCUL-derived integrity engine. Per-window CV signals -> fused risk timeseries -> flagged segments with timestamps. Output is integrity CONFIDENCE, never auto-reject.

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8003
```

## Modules to build
- `app/face.py` — presence + identity (RetinaFace/ArcFace)
- `app/gaze.py` — MediaPipe mesh -> gaze/head-pose look-away
- `app/objects.py` — YOLO person (multi-person) + phone/tablet
- `app/fusion.py` — per-window signals -> risk score -> anomaly flags

Build against `/contracts`. Keep inputs/outputs matching the schemas there.
