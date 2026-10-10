# CodeSense — AI Code-Comprehension Hiring Platform

> Anyone can prompt an AI to write code. Companies can't find people who can tell
> when that code is **wrong**. We measure that, proctor it so it's trustworthy,
> and turn it into a credential and a standardized pre-interview filter.

Monorepo. Four workstreams, one contract. Everything downstream is built against
the JSON contracts in [`/contracts`](contracts/) — change a contract, tell the team.

## The three AI cores
| Core | What it does | Lives in | Owner |
|------|--------------|----------|-------|
| #1 Grounded test generation | company samples -> fresh items, **oracle-verified** | `services/generation` + `oracle/` | ML |
| #2 Comprehension interviewer | present code -> ASR -> AST grounding -> NLI scoring -> adapt | `services/interview` + `services/scoring` | ML + Ilsa |
| #3 Proctoring & integrity | face/gaze/objects/audio -> fused risk score | `services/proctoring` | CV |

Gateway, auth, DB, orchestration: `services/api` (Backend). Frontend: `frontend/` (Ilsa).

## Repo map
```
contracts/     the locked schemas — SOURCE OF TRUTH for all 4 people
data/          seed_bank.json — oracle-verified items to build on
oracle/        the verification harness (Core AI #1's spine)
services/
  api/         FastAPI gateway, auth, Postgres, orchestrator        [Backend]
  generation/  Core AI #1 — RAG generation + oracle client          [ML]
  scoring/     Core AI #2 — AST grounding + NLI explanation scoring  [ML]
  proctoring/  Core AI #3 — CV integrity engine (OCUL-derived)       [CV]
  interview/   session orchestrator + ASR + adaptive follow-up       [Ilsa]
frontend/      Next.js + Monaco + proctor cam                        [Ilsa]
docs/          architecture pointer
```

## Quick start (read SETUP below first if you're on VS Code)
```bash
cp .env.example .env            # fill in secrets later; defaults boot locally
docker compose up api db redis frontend   # the light core comes up first
python oracle/verify_seed_bank.py          # prove the seed bank (no docker needed)
```
- API:       http://localhost:8000/docs
- Frontend:  http://localhost:3000
- Heavy ML/CV services (`generation`, `scoring`, `proctoring`, `interview`) pull big
  model deps — bring them up one at a time once you're working on them:
  `docker compose up scoring`.

## SETUP — VS Code
1. **Open the workspace, not the folder.** `File -> Open Workspace from File...` ->
   `codesense.code-workspace`. This gives you one window with Python + TypeScript
   roots side by side and the right settings per folder.
2. Install the recommended extensions when VS Code prompts (list in `.vscode/extensions.json`):
   Python, Pylance, Ruff, Docker, ESLint, Prettier, Tailwind CSS IntelliSense.
3. **Python** (each service is its own venv so deps don't collide):
   ```bash
   cd services/api && python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
   Then in VS Code bottom-right, select that `.venv` as the interpreter for that folder.
4. **Frontend**:
   ```bash
   cd frontend && npm install && npm run dev
   ```
5. Run the oracle to confirm your machine is good: `python oracle/verify_seed_bank.py`
   — you should see five `VERIFIED (fault bites)` lines.

## Branching
`main` protected. One branch per workstream: `ml/*`, `cv/*`, `be/*`, `fe/*`.
PRs reference the contract they touch. CI runs the oracle + schema validation.
