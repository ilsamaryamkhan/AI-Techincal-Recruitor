"""Live interview loop — the proctored assessment mode.

How it differs from practice:
  - A session is a SEQUENCE of items, served one at a time.
  - It is ADAPTIVE: after the main answer, the candidate gets a follow-up that
    reacts to what they said (confronts a wrong claim, or probes a right one).
  - It reveals NO feedback mid-interview. Scores exist server-side from the first
    answer, but the candidate only sees a completion summary at the end. Recruiters
    read the detail in the pool.

Each item runs as two turns: a "main" turn (scored) and a "followup" turn
(recorded, not scored — its job is to show adaptivity and give the recruiter a
second data point to read). When the last item's follow-up is answered, the
session finalizes into a scored session, so the candidate flows into the
recruiter pool exactly like a practice session does.
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Item, InterviewSession
from ..deps import get_current_user
from ..schemas import to_candidate_view
from ..grading import grade_submission

router = APIRouter(prefix="/interview", tags=["interview"])

INTERVIEW_LEN = 3
# a varied default order so an un-filtered interview spans fault families
PREFERRED = ["D1-1", "D1-3", "D3-1", "D1-2", "D3-2"]


class StartIn(BaseModel):
    domain: str | None = None
    level: str | None = None


class AnswerIn(BaseModel):
    transcript: str


class ProctorIn(BaseModel):
    integrity_confidence: float = 1.0        # 0..1, higher = cleaner
    risk_score: int = 0                       # 0..100
    camera_available: bool = True
    flagged_segments: list[dict] = []         # [{t, type, severity, note}]
    counts: dict = {}                         # {no_face: n, paste: n, ...}
    risk_timeseries: list[dict] = []          # [{t, risk}]


def _pick_items(db: Session, domain: str | None, level: str | None) -> list[Item]:
    q = db.query(Item)
    if domain: q = q.filter(Item.domain == domain)
    if level:  q = q.filter(Item.level == level)
    rows = q.all()
    rows.sort(key=lambda it: PREFERRED.index(it.id) if it.id in PREFERRED else 99)
    return rows[:INTERVIEW_LEN]


def _session_scores(main_turns: list[dict]) -> dict:
    keys = ["verify_score", "detection", "explanation_quality", "calibration", "coverage_required"]
    agg = {}
    for k in keys:
        vals = [t["scoring"].get(k, 0) for t in main_turns if t.get("scoring")]
        agg[k] = round(sum(vals) / len(vals), 1) if vals else 0
    agg["fluent_wrongness_count"] = sum(len(t.get("fluent_wrongness_flags", [])) for t in main_turns)
    return agg


def _owned(db: Session, sid: str, user) -> InterviewSession:
    s = db.query(InterviewSession).filter(InterviewSession.id == sid).first()
    if not s:
        raise HTTPException(404, "Session not found")
    if s.candidate_id != user.id:
        raise HTTPException(403, "Not your session")
    return s


def _current_item_view(db: Session, s: InterviewSession) -> dict:
    item_id = s.data["item_ids"][s.data["idx"]]
    item = db.query(Item).filter(Item.id == item_id).first()
    view = to_candidate_view(item.payload)
    return view


def _progress(s: InterviewSession) -> dict:
    return {"index": s.data["idx"], "total": len(s.data["item_ids"]), "stage": s.data["stage"]}


@router.post("/start")
def start(body: StartIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user.role != "candidate":
        raise HTTPException(403, "Only candidates take interviews")
    items = _pick_items(db, body.domain, body.level)
    if not items:
        raise HTTPException(400, "No items match that domain/level")
    sid = f"iv_{uuid.uuid4().hex[:12]}"
    # a live interview is scoped to one company (the first item's) for the demo
    company_id = items[0].company_id
    s = InterviewSession(
        id=sid, candidate_id=user.id, company_id=company_id, type="live_interview",
        domain=body.domain or "core_se", level=body.level or items[0].level,
        proctored=False, status="in_progress",
        data={"item_ids": [it.id for it in items], "idx": 0, "stage": "main",
              "turns": [], "pending_followup": None},
    )
    db.add(s); db.commit()
    return {"session_id": sid, **_progress(s),
            "item": _current_item_view(db, s), "company_id": company_id}


@router.get("/{sid}")
def resume(sid: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    s = _owned(db, sid, user)
    if s.status != "in_progress":
        return {"session_id": sid, "done": True, "status": s.status}
    out = {"session_id": sid, **_progress(s), "company_id": s.company_id}
    if s.data["stage"] == "followup":
        out["followup"] = s.data.get("pending_followup")
    else:
        out["item"] = _current_item_view(db, s)
    return out


@router.post("/{sid}/proctor")
def proctor(sid: str, body: ProctorIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Store the proctoring summary for a session and mark it proctored.
    The browser accumulates signals (tab-switch, paste, face presence, multiple
    faces) and posts the rollup here — typically once when the interview ends.
    No video is sent; only the derived signals."""
    s = _owned(db, sid, user)
    data = dict(s.data)
    data["proctoring"] = {
        "integrity_confidence": max(0.0, min(1.0, body.integrity_confidence)),
        "risk_score": max(0, min(100, body.risk_score)),
        "camera_available": body.camera_available,
        "flagged_segments": body.flagged_segments,
        "counts": body.counts,
        "risk_timeseries": body.risk_timeseries,
    }
    s.data = data
    s.proctored = True
    db.commit()
    return {"ok": True, "proctored": True}


@router.post("/{sid}/answer")
def answer(sid: str, body: AnswerIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    s = _owned(db, sid, user)
    if s.status != "in_progress":
        raise HTTPException(400, "Interview already finished")
    if not body.transcript.strip():
        raise HTTPException(400, "Answer is empty")

    data = dict(s.data)            # copy so SQLAlchemy sees a new JSON object
    idx = data["idx"]
    item_id = data["item_ids"][idx]
    item = db.query(Item).filter(Item.id == item_id).first()

    if data["stage"] == "main":
        # grade the main answer server-side, record the turn, hand back the adaptive follow-up
        result = grade_submission(item.payload, body.transcript)
        data["turns"].append({
            "turn_id": f"t{len(data['turns'])+1}", "item_id": item_id, "stage": "main",
            "ts": datetime.utcnow().isoformat(), "ai_prompt": item.payload.get("prompt", ""),
            "candidate_input": {"transcript": body.transcript},
            "scoring": result["scores"],
            "fluent_wrongness_flags": result["fluent_wrongness"],
            "adaptive_followup": {"prompt": result["followup"]},
        })
        data["stage"] = "followup"
        data["pending_followup"] = result["followup"]
        data["graded_by"] = result["graded_by"]
        s.data = data; db.commit()
        # NO scores leak to the candidate
        return {"recorded": True, "stage": "followup",
                "followup": result["followup"], "index": idx, "total": len(data["item_ids"])}

    # stage == "followup": record it (not scored), then advance or finish
    data["turns"].append({
        "turn_id": f"t{len(data['turns'])+1}", "item_id": item_id, "stage": "followup",
        "ts": datetime.utcnow().isoformat(), "ai_prompt": data.get("pending_followup", ""),
        "candidate_input": {"transcript": body.transcript},
    })
    data["idx"] = idx + 1
    data["stage"] = "main"
    data["pending_followup"] = None

    if data["idx"] < len(data["item_ids"]):
        s.data = data; db.commit()
        return {"recorded": True, "stage": "main", "index": data["idx"],
                "total": len(data["item_ids"]), "item": _current_item_view(db, s)}

    # finished — finalize into a scored session the recruiter pool will read
    main_turns = [t for t in data["turns"] if t.get("stage") == "main"]
    scores = _session_scores(main_turns)
    data["scores"] = scores
    s.data = data
    s.status = "scored"
    s.completed_at = datetime.utcnow()
    db.commit()
    return {"recorded": True, "done": True, "summary": {
        "items": len(data["item_ids"]),
        "verify_score": round(scores["verify_score"]),
        "company_id": s.company_id,
    }}
