"""Turn a candidate's scored sessions into the numbers a recruiter reads.

The source of truth is the InterviewSession rows written by practice.submit
(and, later, the live interview). We aggregate on read rather than caching a
rolling score on the profile, so a recruiter always sees current data and the
credential rule can change without a migration.

The credential deliberately gates on *calibration* and *fluent wrongness*, not
just the headline score. That is the whole product thesis: a candidate who
explains fluently but can't tell when AI-written code is wrong is exactly the
hire asaanHire is built to catch, and the pool view has to make that visible.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any


def _primary_scoring(session_data: dict) -> dict:
    """The scoring blob for a session. Practice writes it under turns[0].scoring."""
    turns = session_data.get("turns") or []
    if turns and isinstance(turns[0], dict) and turns[0].get("scoring"):
        return turns[0]["scoring"]
    # fallbacks for other shapes
    return session_data.get("scores") or session_data.get("scoring") or {}


def _fluent_flags(session_data: dict) -> list[dict]:
    """Every confident-but-wrong claim recorded across the session's turns."""
    flags: list[dict] = []
    for t in session_data.get("turns") or []:
        if isinstance(t, dict):
            flags.extend(t.get("fluent_wrongness_flags") or [])
    return flags


def _avg(nums: list[float]) -> float:
    return round(sum(nums) / len(nums), 1) if nums else 0.0


def _rollup(sessions: list) -> dict[str, Any]:
    """Shared number-crunching for both the list row and the detail page."""
    scored = [s for s in sessions if s.status == "scored"]
    verify, detection, explanation, calibration, coverage = [], [], [], [], []
    fluent_total = 0
    items: set[str] = set()
    domains: dict[str, int] = {}
    companies: set[str] = set()
    last_active: datetime | None = None

    for s in scored:
        data = s.data or {}
        # an interview stores session-level `scores`; practice stores it on turns[0]
        sc = data.get("scores") or _primary_scoring(data)
        if "verify_score" in sc:       verify.append(sc["verify_score"])
        if "detection" in sc:          detection.append(sc["detection"])
        if "explanation_quality" in sc: explanation.append(sc["explanation_quality"])
        if "calibration" in sc:        calibration.append(sc["calibration"])
        if "coverage_required" in sc:  coverage.append(sc["coverage_required"])
        fluent_total += len(_fluent_flags(data))
        # practice: one item_id; interview: a list of item_ids
        for iid in (data.get("item_ids") or ([data["item_id"]] if data.get("item_id") else [])):
            items.add(iid)
        if s.domain: domains[s.domain] = domains.get(s.domain, 0) + 1
        if s.company_id: companies.add(s.company_id)
        ts = s.completed_at or s.created_at
        if ts and (last_active is None or ts > last_active):
            last_active = ts

    verify_avg = _avg(verify)
    items_n = len(items)

    # ---- the credential rule ----
    # verified  : consistently strong AND never confidently wrong
    # developing: shows comprehension but not yet clean enough to vouch for
    # unverified: not enough signal, or weak
    if verify_avg >= 70 and items_n >= 2 and fluent_total == 0:
        credential = "verified"
    elif verify_avg >= 55 and items_n >= 1:
        credential = "developing"
    else:
        credential = "unverified"

    return {
        "verify_score": round(verify_avg),
        "verify_best": round(max(verify)) if verify else 0,
        "detection": round(_avg(detection)),
        "explanation_quality": round(_avg(explanation)),
        "calibration": round(_avg(calibration)),
        "coverage_required": round(_avg(coverage)),
        "fluent_wrongness_total": fluent_total,
        "items_attempted": items_n,
        "sessions": len(scored),
        "domains": sorted(domains, key=domains.get, reverse=True),
        "top_domain": max(domains, key=domains.get) if domains else None,
        "companies": sorted(companies),
        "credential": credential,
        "verified": credential == "verified",
        "last_active": last_active.isoformat() if last_active else None,
    }


def summarize_candidate(user, sessions: list) -> dict[str, Any]:
    """One row in the recruiter pool."""
    roll = _rollup(sessions)
    roll.update({
        "user_id": user.id,
        "name": user.full_name or user.email.split("@")[0],
        "email": user.email,
    })
    return roll


def detail_candidate(user, sessions: list) -> dict[str, Any]:
    """Full candidate profile: credential, the fluent-wrongness record, history."""
    roll = _rollup(sessions)
    scored = sorted(
        [s for s in sessions if s.status == "scored"],
        key=lambda s: (s.completed_at or s.created_at or datetime.min),
        reverse=True,
    )

    history, fluent_record = [], []
    for s in scored:
        data = s.data or {}
        sc = data.get("scores") or _primary_scoring(data)
        item_ids = data.get("item_ids")
        # practice sessions carry one item_id; interviews carry a list
        label = (f"Interview · {len(item_ids)} items" if item_ids
                 else data.get("item_id"))
        turn_flags = _fluent_flags(data)
        proc = data.get("proctoring")
        history.append({
            "session_id": s.id,
            "item_id": label,
            "company_id": s.company_id,
            "domain": s.domain,
            "level": s.level,
            "type": s.type,
            "proctored": s.proctored,
            "integrity": round(proc["integrity_confidence"] * 100) if proc else None,
            "proctor_flags": len(proc.get("flagged_segments", [])) if proc else 0,
            "verify_score": round(sc.get("verify_score", 0)),
            "calibration": round(sc.get("calibration", 0)),
            "fluent_wrongness_count": len(turn_flags),
            "graded_by": data.get("graded_by"),
            "completed_at": (s.completed_at or s.created_at).isoformat()
                            if (s.completed_at or s.created_at) else None,
        })
        # pull each flag's own item_id from its turn so the record stays precise
        for t in data.get("turns") or []:
            for f in (t.get("fluent_wrongness_flags") or []):
                fluent_record.append({
                    "item_id": t.get("item_id") or data.get("item_id"),
                    "company_id": s.company_id,
                    "claim": f.get("claim"),
                    "contradicts": f.get("contradicts"),
                })

    # a short, human reason the credential reads the way it does
    if roll["credential"] == "verified":
        basis = (f"{roll['items_attempted']} items, avg {roll['verify_score']} verify, "
                 f"no confidently-wrong claims.")
    elif roll["credential"] == "developing":
        if roll["fluent_wrongness_total"]:
            basis = (f"Explains well but made {roll['fluent_wrongness_total']} "
                     f"confidently-wrong claim(s) — calibration {roll['calibration']}.")
        else:
            basis = f"On track — avg {roll['verify_score']} verify over {roll['items_attempted']} item(s)."
    else:
        basis = "Not enough signal yet, or comprehension below threshold."

    # surface the most recent proctored session's integrity report, if any
    proctoring = None
    for s in scored:  # already newest-first
        p = (s.data or {}).get("proctoring")
        if p:
            proctoring = {**p, "session_id": s.id}
            break

    return {
        **roll,
        "user_id": user.id,
        "name": user.full_name or user.email.split("@")[0],
        "email": user.email,
        "credential_basis": basis,
        "fluent_wrongness_record": fluent_record,
        "history": history,
        "proctoring": proctoring,
    }
