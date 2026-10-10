"""Practice: submit an explanation, get it graded, persist the session.

Grading happens SERVER-SIDE against the full item (answers never go to the client
pre-submission). Practice is a teaching mode, so the response reveals which
observations were covered/missed as feedback — a live interview would not."""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Item, InterviewSession
from ..deps import get_current_user
from ..grading import grade_submission

router = APIRouter(prefix="/practice", tags=["practice"])


class SubmitIn(BaseModel):
    item_id: str
    explanation: str


@router.post("/submit")
def submit(body: SubmitIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = db.query(Item).filter(Item.id == body.item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    if not body.explanation.strip():
        raise HTTPException(400, "Explanation is empty")

    result = grade_submission(item.payload, body.explanation)  # full item, server-side

    # persist as a practice session (recruiters read these later)
    sid = f"ses_{uuid.uuid4().hex[:12]}"
    session = InterviewSession(
        id=sid, candidate_id=user.id, company_id=item.company_id, type="practice",
        domain=item.domain, level=item.level, proctored=False, status="scored",
        data={
            "item_id": item.id,
            "turns": [{
                "turn_id": "t1", "item_id": item.id, "ts": datetime.utcnow().isoformat(),
                "candidate_input": {"transcript": body.explanation},
                "scoring": result["scores"],
                "fluent_wrongness_flags": result["fluent_wrongness"],
                "adaptive_followup": {"prompt": result["followup"]},
            }],
            "feedback": result["feedback"],
            "graded_by": result["graded_by"],
        },
        completed_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()

    return {
        "session_id": sid,
        "scores": result["scores"],
        "feedback": result["feedback"],
        "fluent_wrongness": result["fluent_wrongness"],
        "flagged_decoy": result["flagged_decoy"],
        "identified_core_issue": result["identified_core_issue"],
        "grounding_facts": result["grounding_facts"],
        "followup": result["followup"],
        "graded_by": result["graded_by"],
    }
