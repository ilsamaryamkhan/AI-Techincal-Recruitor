"""Company list — used by the signup dropdown and company/domain filters."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Company

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("")
def list_companies(db: Session = Depends(get_db)):
    rows = db.query(Company).order_by(Company.name).all()
    return [{"id": c.id, "name": c.name} for c in rows]
