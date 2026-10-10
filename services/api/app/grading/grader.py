"""The grader. Produces a normalized grade from either the LLM path (Groq) or the
offline rule-based path, then runs the shared scoring fusion. Both paths feed the
SAME normalized structure, so scores are comparable however grading happened.
"""
from __future__ import annotations
import re
from . import llm
from .grounding import ground
from .scoring import normalized_template, compute_scores


def grade_submission(item: dict, explanation: str) -> dict:
    """item = FULL GeneratedItem (with expected_observations, fault_label, decoys).
    Returns a result dict for the API/UI. Answer fields are used here but the caller
    decides what to reveal (practice reveals feedback; a live interview would not)."""
    code = item["artifact"]["files"][0]["content"]
    g = ground(item["language"], code)

    grade = _grade_llm(item, explanation, g) or _grade_offline(item, explanation, g)
    scores = compute_scores(item, grade)
    followup = _followup(item, explanation, g, grade)

    # attach the observation statements so the UI can show covered/missed as feedback
    obs_by_id = {o["obs_id"]: o for o in item.get("expected_observations", [])}
    feedback = []
    for gobs in grade["observations"]:
        o = obs_by_id.get(gobs["obs_id"], {})
        feedback.append({
            "obs_id": gobs["obs_id"], "statement": o.get("statement", ""),
            "required": o.get("required", False), "covered": gobs.get("covered", False),
        })

    return {
        "scores": scores,
        "feedback": feedback,
        "fluent_wrongness": grade.get("fluent_wrongness", []),
        "flagged_decoy": grade.get("flagged_decoy", False),
        "identified_core_issue": grade.get("identified_core_issue", False),
        "grounding_facts": g["facts"],
        "followup": followup,
        "graded_by": grade.get("_source", "offline"),
    }


# --------------------------------------------------------------------------- LLM path
_SYS = (
    "You are a strict senior engineer grading whether a candidate truly UNDERSTANDS code "
    "they were asked to explain. You are given: the code, FACTS derived from the code "
    "(ground truth), the observations a correct explanation should make, and any decoys "
    "(things that look wrong but are actually fine). Judge the candidate's explanation. "
    "A confident claim that CONTRADICTS the ground-truth facts is 'fluent wrongness' and "
    "must be flagged. Reply with ONLY a JSON object."
)

def _grade_llm(item: dict, explanation: str, g: dict) -> dict | None:
    if not llm.available():
        return None
    obs = [{"obs_id": o["obs_id"], "statement": o["statement"], "required": o.get("required", False)}
           for o in item.get("expected_observations", [])]
    decoys = [{"looks_wrong": d["why_it_looks_wrong"], "actually_fine": d["why_its_actually_fine"]}
              for d in item.get("decoys", [])]
    user = (
        f"CODE ({item['language']}):\n{item['artifact']['files'][0]['content']}\n\n"
        f"GROUND-TRUTH FACTS:\n- " + "\n- ".join(g["facts"] or ["(none)"]) + "\n\n"
        f"THE REAL ISSUE: {item.get('fault_label', {}).get('description', 'n/a')}\n\n"
        f"OBSERVATIONS A GOOD EXPLANATION MAKES:\n" +
        "\n".join(f"- {o['obs_id']} ({'required' if o['required'] else 'bonus'}): {o['statement']}" for o in obs) +
        f"\n\nDECOYS (flagging these as bugs is WRONG):\n" +
        ("\n".join(f"- looks wrong: {d['looks_wrong']} | actually fine: {d['actually_fine']}" for d in decoys) or "(none)") +
        f"\n\nCANDIDATE EXPLANATION:\n{explanation}\n\n"
        "Return JSON with EXACTLY this shape:\n"
        '{"observations":[{"obs_id":"o1","covered":true|false}],'
        '"identified_core_issue":true|false,'
        '"fluent_wrongness":[{"claim":"...","contradicts":"..."}],'
        '"flagged_decoy":true|false,'
        '"depth":0.0-1.0,"terminology":0.0-1.0}'
    )
    data = llm.chat_json(_SYS, user)
    if not data or "observations" not in data:
        return None
    # normalize into our template (defensive against missing keys)
    grade = normalized_template(item)
    covered_ids = {o.get("obs_id"): bool(o.get("covered")) for o in data.get("observations", [])}
    for gobs in grade["observations"]:
        gobs["covered"] = covered_ids.get(gobs["obs_id"], False)
    grade["identified_core_issue"] = bool(data.get("identified_core_issue"))
    grade["fluent_wrongness"] = data.get("fluent_wrongness", []) or []
    grade["flagged_decoy"] = bool(data.get("flagged_decoy"))
    grade["depth"] = float(data.get("depth", 0) or 0)
    grade["terminology"] = float(data.get("terminology", 0) or 0)
    grade["_source"] = "groq"
    return grade


# --------------------------------------------------------------------------- offline path
def _grade_offline(item: dict, explanation: str, g: dict) -> dict:
    """Keyword/heuristic grader. Works with no network, on the seed items. Weaker on
    unusual phrasing, but deterministic — the safety net when the LLM is unreachable."""
    text = explanation.lower()
    grade = normalized_template(item)

    # coverage: an observation counts as covered if enough of its salient terms appear
    for gobs, o in zip(grade["observations"], item.get("expected_observations", [])):
        gobs["covered"] = _mentions(text, o["statement"])

    fault_id = item.get("fault_label", {}).get("fault_id", "")
    flags = g.get("flags", {})

    # identified core issue + fluent-wrongness, per fault family
    fw = []
    core = False
    if fault_id == "EFF-LIST-IN-LOOP":
        core = ("n^2" in text or "n²" in text or "quadratic" in text or
                ("list" in text and ("o(n)" in text and "membership" in text)))
        if _claims_linear(text) and flags.get("list_membership_in_loop"):
            fw.append({"claim": "explanation calls it O(n) / hash-set lookup",
                       "contradicts": "`seen` is a list, so membership is O(n) → overall O(n^2)"})
    elif fault_id == "OOP-MUTABLE-DEFAULT":
        core = "default" in text and ("mutable" in text or "shared" in text or "same list" in text or "persist" in text)
    elif fault_id == "CORR-OFF-BY-ONE":
        core = ("off-by-one" in text or "off by one" in text or
                ("<=" in explanation and "<" in explanation) or "last element" in text or "boundary" in text)
    elif fault_id == "DB-WRONG-JOIN":
        core = ("duplicat" in text or "fan" in text or "one-to-many" in text or "inflat" in text or "double" in text)
    elif fault_id == "DB-GROUPBY-ERR":
        core = ("count(*)" in text or "null" in text or "count(o" in text or "zero" in text)
    grade["identified_core_issue"] = core
    grade["fluent_wrongness"] = fw

    # decoy flagged? crude: did they call out the decoy's location/term as a bug
    decoy_hit = False
    for d in item.get("decoys", []):
        loc = d.get("location", {})
        # if they mention "overflow" for the python binary search decoy, that's a decoy flag
        if fault_id == "CORR-OFF-BY-ONE" and "overflow" in text:
            decoy_hit = True
        if "missing group by" in text and item.get("domain") == "database":
            decoy_hit = True
    grade["flagged_decoy"] = decoy_hit

    # rough depth/terminology from length + presence of precise terms
    grade["depth"] = min(1.0, len(text.split()) / 60.0)
    grade["terminology"] = 1.0 if any(t in text for t in
        ["complexity", "o(n", "edge case", "invariant", "join", "null", "encapsulation"]) else 0.4
    grade["_source"] = "offline"
    return grade


def _mentions(text: str, statement: str) -> bool:
    """covered if >=40% of the statement's salient (len>3) words appear."""
    words = [w for w in re.findall(r"[a-zA-Z()]+", statement.lower()) if len(w) > 3]
    if not words:
        return False
    hits = sum(1 for w in words if w in text)
    return hits / len(words) >= 0.4

def _claims_linear(text: str) -> bool:
    return ("o(n)" in text and "o(n^2)" not in text and "o(n²)" not in text) or "hash set" in text or "hashset" in text


# --------------------------------------------------------------------------- follow-up
def _followup(item: dict, explanation: str, g: dict, grade: dict) -> str:
    if grade.get("fluent_wrongness"):
        fw = grade["fluent_wrongness"][0]
        # try LLM for a sharp, specific probe; fall back to a templated one
        t = llm.chat_text(
            "You are an interviewer. Ask ONE short pointed follow-up (max 25 words) that makes the "
            "candidate confront a wrong claim. No preamble.",
            f"Code facts: {g['facts']}\nCandidate wrongly said: {fw['claim']}\nReality: {fw['contradicts']}\nAsk one question.",
        )
        return t or "You said it's O(n). Walk me through what `in seen` costs on the 10th iteration."
    # if they got it, push for depth
    t = llm.chat_text(
        "You are an interviewer. Ask ONE short follow-up (max 25 words) that pushes for deeper understanding. No preamble.",
        f"Code facts: {g['facts']}\nCandidate explanation: {explanation[:600]}\nAsk one deeper question.",
    )
    return t or "Good. Now how would you fix it, and what does that change about the complexity?"
