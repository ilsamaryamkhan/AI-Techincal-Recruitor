"""SQLAlchemy models — the asaanHire data model.

Design note for the team: each "rich" entity (Item, Session, Profile) keeps a JSON
`data`/`payload` blob for the full contract shape, plus a few flat columns we filter on.
That means we never fight the DB when the contract grows a field — it just rides in JSON.
The flat columns exist only so we can query (WHERE domain=... AND level=...).
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from .db import Base


class Company(Base):
    __tablename__ = "companies"
    id = Column(String, primary_key=True)          # slug, e.g. "devsinc"
    name = Column(String, nullable=False)          # display, e.g. "Devsinc"
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="company")
    items = relationship("Item", back_populates="company")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)          # candidate | company | recruiter
    full_name = Column(String, nullable=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=True)  # for company/recruiter users
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="users")
    profile = relationship("CandidateProfile", back_populates="user", uselist=False)


class Item(Base):
    """A GeneratedItem (see contracts/generated_item.schema.json).
    `payload` holds the COMPLETE item including SERVER-ONLY fault_label + verification.
    Never serialize `payload` straight to a candidate — use schemas.to_candidate_view()."""
    __tablename__ = "items"
    id = Column(String, primary_key=True)          # e.g. "D1-1"
    company_id = Column(String, ForeignKey("companies.id"), index=True)
    domain = Column(String, index=True)            # core_se | web | database | qa | ml
    level = Column(String, index=True)             # associate | engineer | senior
    mode = Column(String)                          # comprehension | solve | debug | optimize
    language = Column(String)
    payload = Column(JSON, nullable=False)         # the full contract object
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="items")


class InterviewSession(Base):
    """See contracts/interview_session.schema.json. Runtime state rides in `data`."""
    __tablename__ = "sessions"
    id = Column(String, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("users.id"), index=True)
    company_id = Column(String, ForeignKey("companies.id"), index=True)
    type = Column(String)                          # practice | live_interview
    domain = Column(String)
    level = Column(String)
    proctored = Column(Boolean, default=False)
    status = Column(String, default="in_progress") # in_progress | scored | needs_review
    data = Column(JSON, default=dict)              # turns, proctoring, scores
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class CandidateProfile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True)
    build_score = Column(Float, nullable=True)
    verify_score = Column(Float, nullable=True)    # the headline comprehension score
    is_public = Column(Boolean, default=False)
    data = Column(JSON, default=dict)              # calibration_curve, per-concept mastery, etc.
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")
