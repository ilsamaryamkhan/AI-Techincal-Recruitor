"""Register, login, me. JSON bodies (not form) so the frontend fetch stays simple."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, CandidateProfile
from ..schemas import RegisterIn, LoginIn, TokenOut, UserOut
from ..security import hash_password, verify_password, create_access_token
from ..deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

VALID_ROLES = {"candidate", "company", "recruiter"}


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if body.role not in VALID_ROLES:
        raise HTTPException(400, f"role must be one of {VALID_ROLES}")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(409, "Email already registered")
    user = User(
        email=body.email, hashed_password=hash_password(body.password),
        role=body.role, full_name=body.full_name, company_id=body.company_id,
    )
    db.add(user)
    db.flush()
    # every candidate gets a (private) profile shell up front
    if user.role == "candidate":
        db.add(CandidateProfile(user_id=user.id, is_public=False, data={}))
    db.commit()
    return TokenOut(access_token=create_access_token(user.email, user.role), role=user.role)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return TokenOut(access_token=create_access_token(user.email, user.role), role=user.role)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
