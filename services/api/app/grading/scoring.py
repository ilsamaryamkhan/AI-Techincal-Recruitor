"""Pure scoring fusion. Takes a NORMALIZED grade (same shape from LLM or offline path)
plus the item, and computes the Verify score + sub-scores. One formula, one source of
truth — the grading path only decides *what was covered*, never the final number."""
from __future__ import annotations


def normalized_template(item: dict) -> dict:
    """Empty grade skeleton with one entry per expected observation."""
    return {
        "observations": [{"obs_id": o["obs_id"], "covered": False, "evidence": ""}
                         for o in item.get("expected_observations", [])],
        "identified_core_issue": False,
        "fluent_wrongness": [],     # [{claim, contradicts}]
        "flagged_decoy": False,
        "depth": 0.0,
        "terminology": 0.0,
    }


def compute_scores(item: dict, grade: dict) -> dict:
    obs = item.get("expected_observations", [])
    required = [o["obs_id"] for o in obs if o.get("required")]
    optional = [o["obs_id"] for o in obs if not o.get("required")]
    covered = {g["obs_id"] for g in grade["observations"] if g.get("covered")}

    cov_req = len([o for o in required if o in covered]) / max(1, len(required))
    cov_opt = (len([o for o in optional if o in covered]) / len(optional)) if optional else 0.0

    detection = 1.0 if grade.get("identified_core_issue") else (0.6 * cov_req)
    explanation = 0.6 * cov_req + 0.2 * cov_opt + 0.1 * float(grade.get("depth", 0)) \
                  + 0.1 * float(grade.get("terminology", 0))
    calibration = 1.0 - (0.5 if grade.get("flagged_decoy") else 0.0)

    r = item.get("rubric", {})
    w_det = r.get("detection_weight", 0.35)
    w_exp = r.get("explanation_weight", 0.40)
    w_cal = r.get("calibration_weight", 0.25)

    base = 100 * (w_det * detection + w_exp * explanation + w_cal * calibration)

    # fluent-wrongness is the cardinal sin: each contradicted claim scales the score down
    n_fw = len(grade.get("fluent_wrongness", []))
    fw_penalty = min(0.4, 0.2 * n_fw)
    verify = round(max(0.0, base * (1 - fw_penalty)))

    return {
        "verify_score": verify,
        "detection": round(detection * 100),
        "explanation_quality": round(explanation * 100),
        "calibration": round(calibration * 100),
        "coverage_required": round(cov_req * 100),
        "fluent_wrongness_count": n_fw,
        "fw_penalty_pct": round(fw_penalty * 100),
    }
