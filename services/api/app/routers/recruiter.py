"""Recruiter dashboard: the candidate pool and the verified credential.

Everything here is gated to company/recruiter roles — candidates never see the
pool or anyone else's profile. The numbers are aggregated on read from the
candidate's scored sessions (see app/aggregate.py), so the dashboard is always
current and the credential rule can evolve without a migration.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, InterviewSession
from ..deps import require_role
from ..aggregate import summarize_candidate, detail_candidate

router = APIRouter(prefix="/recruiter", tags=["recruiter"])

SORTS = {
    "verify":      lambda c: (-c["verify_score"], c["fluent_wrongness_total"]),
    "calibration": lambda c: -c["calibration"],
    "fluent":      lambda c: -c["fluent_wrongness_total"],   # most confidently-wrong first
    "recent":      lambda c: c["last_active"] or "",
}


def _sessions_by_candidate(db: Session) -> dict[int, list]:
    rows = db.query(InterviewSession).filter(InterviewSession.status == "scored").all()
    out: dict[int, list] = {}
    for s in rows:
        out.setdefault(s.candidate_id, []).append(s)
    return out


@router.get("/stats")
def pool_stats(db: Session = Depends(get_db),
               user=Depends(require_role("company", "recruiter"))):
    by_cand = _sessions_by_candidate(db)
    candidates = db.query(User).filter(User.role == "candidate").all()
    rows = [summarize_candidate(c, by_cand.get(c.id, [])) for c in candidates
            if by_cand.get(c.id)]
    verified = sum(1 for r in rows if r["verified"])
    flagged = sum(1 for r in rows if r["fluent_wrongness_total"] > 0)
    avg_verify = round(sum(r["verify_score"] for r in rows) / len(rows)) if rows else 0
    return {
        "candidates": len(rows),
        "verified": verified,
        "fluent_wrongness_flagged": flagged,
        "avg_verify": avg_verify,
    }


@router.get("/candidates")
def list_candidates(
    domain: str | None = Query(None),
    company_id: str | None = Query(None),
    level: str | None = Query(None),
    credential: str | None = Query(None, description="verified | developing | unverified"),
    min_verify: int = Query(0, ge=0, le=100),
    sort: str = Query("verify"),
    db: Session = Depends(get_db),
    user=Depends(require_role("company", "recruiter")),
):
    by_cand = _sessions_by_candidate(db)
    candidates = db.query(User).filter(User.role == "candidate").all()

    rows = []
    for c in candidates:
        sess = by_cand.get(c.id)
        if not sess:
            continue
        if domain:     sess = [s for s in sess if s.domain == domain]
        if company_id: sess = [s for s in sess if s.company_id == company_id]
        if level:      sess = [s for s in sess if s.level == level]
        if not sess:
            continue
        row = summarize_candidate(c, sess)
        if row["verify_score"] < min_verify:
            continue
        if credential and row["credential"] != credential:
            continue
        rows.append(row)

    rows.sort(key=SORTS.get(sort, SORTS["verify"]))
    if sort == "recent":
        rows.reverse()
    return rows


@router.get("/candidates/{user_id}")
def candidate_detail(user_id: int, db: Session = Depends(get_db),
                     user=Depends(require_role("company", "recruiter"))):
    cand = db.query(User).filter(User.id == user_id, User.role == "candidate").first()
    if not cand:
        raise HTTPException(404, "Candidate not found")
    sessions = (db.query(InterviewSession)
                .filter(InterviewSession.candidate_id == user_id,
                        InterviewSession.status == "scored").all())
    return detail_candidate(cand, sessions)
