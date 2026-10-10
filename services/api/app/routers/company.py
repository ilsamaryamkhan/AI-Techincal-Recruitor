"""Company test authoring — companies create their own verified items.

The guarantee: an item can only be published if its fault BITES, proven by the
oracle (app.oracle.verify_item) executing the buggy code against the author's
reference. A broken or trivial "test" is rejected at publish time.

Published company items are ordinary Items (same shape as the seed bank), scoped
to the author's company, so they flow into practice, interviews and the recruiter
pool exactly like ours. Answer fields (incl. the executable `check`) are stripped
before anything reaches a candidate by schemas.to_candidate_view().
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Item
from ..deps import require_role
from ..schemas import to_candidate_view
from ..oracle import verify_item
from ..generate import generate_item, extract_text

router = APIRouter(prefix="/company", tags=["company"])

DOMAINS = {"core_se", "database", "web", "qa", "ml"}
LEVELS = {"associate", "engineer", "senior"}
LANGS = {"python", "sql"}
KINDS = {"python_diff", "python_perf", "sql_diff"}


class ItemDraft(BaseModel):
    domain: str
    level: str
    language: str
    prompt: str = Field(min_length=10)
    code: str = Field(min_length=1)
    fault_id: str = Field(min_length=2)
    fault_description: str = Field(min_length=10)
    observations: list[str] = Field(min_length=3)   # first 3 required, rest bonus
    decoy_looks_wrong: str = ""
    decoy_actually_fine: str = ""
    check: dict


def _validate(draft: ItemDraft):
    if draft.domain not in DOMAINS: raise HTTPException(400, f"domain must be one of {sorted(DOMAINS)}")
    if draft.level not in LEVELS:   raise HTTPException(400, f"level must be one of {sorted(LEVELS)}")
    if draft.language not in LANGS: raise HTTPException(400, f"language must be one of {sorted(LANGS)}")
    kind = draft.check.get("kind")
    if kind not in KINDS: raise HTTPException(400, f"check.kind must be one of {sorted(KINDS)}")
    if kind == "python_diff" and not (draft.check.get("reference") and draft.check.get("probe")):
        raise HTTPException(400, "python_diff needs check.reference and check.probe")
    if kind == "python_perf" and not (draft.check.get("reference") and draft.check.get("setup") and draft.check.get("entry")):
        raise HTTPException(400, "python_perf needs check.reference, check.setup and check.entry")
    if kind == "sql_diff" and not (draft.check.get("schema") and draft.check.get("correct")):
        raise HTTPException(400, "sql_diff needs check.schema and check.correct")


def _assemble(draft: ItemDraft, company_id: str, item_id: str) -> dict:
    ext = "sql" if draft.language == "sql" else "py"
    obs = []
    for i, s in enumerate(draft.observations):
        obs.append({"obs_id": f"o{i+1}", "statement": s, "required": i < 3,
                    "concept_tags": ["core"] if i < 3 else ["detail"]})
    decoys = []
    if draft.decoy_looks_wrong and draft.decoy_actually_fine:
        decoys.append({"location": {"file": f"solution.{ext}", "line": 1},
                       "why_it_looks_wrong": draft.decoy_looks_wrong,
                       "why_its_actually_fine": draft.decoy_actually_fine})
    return {
        "item_id": item_id, "company_id": company_id, "domain": draft.domain, "level": draft.level,
        "role_tags": ["backend", f"{draft.level}_se"], "mode": "comprehension", "language": draft.language,
        "blueprint_ref": f"bp_{company_id}_{draft.domain}_{draft.level}", "prompt": draft.prompt,
        "artifact": {"files": [{"path": f"solution.{ext}", "content": draft.code}],
                     "entrypoint": f"solution.{ext}"},
        "fault_label": {"present": True, "fault_id": draft.fault_id, "category": draft.domain,
                        "location": {"file": f"solution.{ext}", "line_start": 1, "line_end": 1, "symbol": ""},
                        "description": draft.fault_description, "severity": "high"},
        "expected_observations": obs, "decoys": decoys,
        "verification": {"method": ["oracle"], "status": "verified", "verified_at": datetime.utcnow().isoformat()},
        "check": draft.check,
        "rubric": {"detection_weight": 0.4, "explanation_weight": 0.4, "calibration_weight": 0.2, "concept_mastery_map": {}},
        "irt": {"a": None, "b": None, "calibrated": False},
        "novelty": {"max_similarity_to_public": 0.0, "passed": True},
        "provenance": {"generated_by": "company_authored", "author_company": company_id,
                       "created_at": datetime.utcnow().isoformat()},
    }


@router.post("/items/verify")
def verify(draft: ItemDraft, user=Depends(require_role("company"))):
    """Dry-run: run the oracle without saving, so the author sees pass/fail live."""
    _validate(draft)
    payload = _assemble(draft, user.company_id or "preview", "PREVIEW")
    return verify_item(payload)


@router.post("/items", status_code=201)
def create(draft: ItemDraft, db: Session = Depends(get_db), user=Depends(require_role("company"))):
    if not user.company_id:
        raise HTTPException(400, "Your account isn't linked to a company")
    _validate(draft)
    item_id = f"{user.company_id[:3].upper()}-{uuid.uuid4().hex[:5]}"
    payload = _assemble(draft, user.company_id, item_id)

    result = verify_item(payload)
    if not result["passed"]:
        raise HTTPException(422, f"Oracle rejected this test — the fault does not bite. {result['summary']}")

    row = Item(id=item_id, company_id=user.company_id, domain=draft.domain, level=draft.level,
               mode="comprehension", language=draft.language, payload=payload)
    db.add(row); db.commit()
    return {"item_id": item_id, "verified": True, "oracle": result["summary"],
            "preview": to_candidate_view(payload)}


@router.post("/generate")
async def generate(
    domain: str = Form(...), level: str = Form(...), language: str = Form("python"),
    position: str = Form(""), source_text: str = Form(""),
    file: UploadFile | None = File(None),
    user=Depends(require_role("company")),
):
    """Turn a plain document + a target role into a verified comprehension draft.

    Upload a document (prose — a JD, a topic list, notes) OR paste source_text; pick the
    domain/level/position. We draft AI-style code with one real fault matched to the role,
    prove it bites with the oracle, and hand back a draft for the author to review and publish.
    """
    if domain not in DOMAINS: raise HTTPException(400, f"domain must be one of {sorted(DOMAINS)}")
    if level not in LEVELS:   raise HTTPException(400, f"level must be one of {sorted(LEVELS)}")
    text = (source_text or "").strip()
    if file is not None:
        raw = await file.read()
        if len(raw) > 2_000_000:
            raise HTTPException(413, "Document too large (max ~2 MB).")
        text = (extract_text(file.filename or "", raw) + "\n" + text).strip()
    if len(text) < 20:
        raise HTTPException(400, "Give a document or some content to generate from (at least a sentence).")
    result = generate_item(domain, level, language, position, text)
    if not result["verified"]:
        raise HTTPException(422, f"Could not produce a biting test from this document. {result['oracle']}")
    return result


@router.get("/items")
def my_items(db: Session = Depends(get_db), user=Depends(require_role("company"))):
    """The authoring company's own bank — full items (they own the answers)."""
    rows = db.query(Item).filter(Item.company_id == user.company_id).order_by(Item.created_at.desc()).all()
    out = []
    for r in rows:
        p = r.payload
        out.append({
            "item_id": r.id, "domain": r.domain, "level": r.level, "language": r.language,
            "prompt": p.get("prompt", ""), "fault_id": p.get("fault_label", {}).get("fault_id", ""),
            "authored": p.get("provenance", {}).get("generated_by") == "company_authored",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return out


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: str, db: Session = Depends(get_db), user=Depends(require_role("company"))):
    row = db.query(Item).filter(Item.id == item_id).first()
    if not row:
        raise HTTPException(404, "Item not found")
    if row.company_id != user.company_id:
        raise HTTPException(403, "Not your company's item")
    if row.payload.get("provenance", {}).get("generated_by") != "company_authored":
        raise HTTPException(403, "Seed items can't be deleted")
    db.delete(row); db.commit()
    return None
