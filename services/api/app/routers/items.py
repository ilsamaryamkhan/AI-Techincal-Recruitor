"""Item endpoints. The candidate-facing routes NEVER return answer fields.
Company/recruiter users can fetch the full item (they own the content)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Item
from ..schemas import to_candidate_view, ItemCandidateOut
from ..deps import get_current_user, require_role

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[ItemCandidateOut])
def list_items(
    company_id: str | None = Query(None),
    domain: str | None = Query(None),
    level: str | None = Query(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    q = db.query(Item)
    if company_id: q = q.filter(Item.company_id == company_id)
    if domain:     q = q.filter(Item.domain == domain)
    if level:      q = q.filter(Item.level == level)
    return [to_candidate_view(it.payload) for it in q.all()]


@router.get("/{item_id}", response_model=ItemCandidateOut)
def get_item(item_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Candidate-safe view — answer fields stripped before the response leaves the server."""
    it = db.query(Item).filter(Item.id == item_id).first()
    if not it:
        raise HTTPException(404, "Item not found")
    return to_candidate_view(it.payload)


@router.get("/{item_id}/full")
def get_item_full(item_id: str, db: Session = Depends(get_db),
                  user=Depends(require_role("company", "recruiter"))):
    """Full item incl. fault_label + verification. Restricted to company/recruiter roles.
    The grader (scoring service) also reads the full payload server-to-server, not via this route."""
    it = db.query(Item).filter(Item.id == item_id).first()
    if not it:
        raise HTTPException(404, "Item not found")
    return it.payload
