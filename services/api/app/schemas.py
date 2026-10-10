"""Pydantic request/response shapes + the candidate-safe item projection.

THE SECURITY RULE (from contracts/README.md):
An item's answer lives in `fault_label`, `verification`, `decoys`, and
`expected_observations`. None of those may reach a candidate's browser, or the
answer leaks in the network tab. to_candidate_view() is the ONLY function that
should build what a candidate receives.
"""
from typing import Optional, Any
from pydantic import BaseModel, EmailStr

# ----- auth -----
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    role: str = "candidate"            # candidate | company | recruiter
    full_name: Optional[str] = None
    company_id: Optional[str] = None   # required for company/recruiter users

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    full_name: Optional[str] = None
    company_id: Optional[str] = None
    class Config:
        from_attributes = True

# ----- items -----
# Exactly the fields a candidate is allowed to see. Anything not here stays server-side.
CANDIDATE_FIELDS = {
    "item_id", "company_id", "domain", "level", "role_tags",
    "mode", "language", "prompt", "artifact",
}
# Fields that carry the answer — asserted-absent in tests so a refactor can't leak them.
# `check` holds the executable reference fix, so it is answer-bearing too.
ANSWER_FIELDS = {"fault_label", "verification", "decoys", "expected_observations", "rubric", "check"}

def to_candidate_view(payload: dict) -> dict:
    """Project a full GeneratedItem down to only what a candidate may receive."""
    return {k: payload[k] for k in CANDIDATE_FIELDS if k in payload}


class ItemCandidateOut(BaseModel):
    item_id: str
    company_id: str
    domain: str
    level: str
    role_tags: list[str] = []
    mode: str
    language: str
    prompt: str
    artifact: dict[str, Any]
