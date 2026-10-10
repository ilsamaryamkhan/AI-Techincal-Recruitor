# API Gateway  [Backend]

FastAPI gateway: auth, roles (candidate/company/recruiter), Postgres models, the interview orchestrator entrypoint, and the practice/eligibility flow. Fans out to the ML/CV services and persists sessions. Owns the rule that strips SERVER-ONLY fields before any item is sent to a candidate.

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Modules to build
- `app/config.py` — env + settings
- `app/db.py` — SQLAlchemy engine/session
- `app/models.py` — User, Company, Domain, GeneratedItem, Session, Profile, Credential
- `app/schemas.py` — pydantic request/response (mirror /contracts)
- `app/routers/auth.py` — register/login, JWT
- `app/routers/companies.py` — company + sample upload
- `app/routers/practice.py` — start practice, submit, eligibility threshold
- `app/routers/interviews.py` — schedule, run turn, fuse score
- `app/routers/profiles.py` — candidate profile, public/private toggle, credential

Build against `/contracts`. Keep inputs/outputs matching the schemas there.
