"""Seed demo candidates so the recruiter pool is populated for the demo.

Idempotent: keyed by email, re-running skips candidates that already exist.
All demo accounts share the password below so judges can log in as any of them.

Run it (from services/api, venv active, AFTER seed_loader):
    python -m app.seed_candidates

The personas are chosen to tell the product story at a glance:
  - verified, strong generalists                     -> the hires you want
  - "fluent but wrong": explains beautifully, low     -> the trap asaanHire
    calibration, confidently-wrong claims                exists to catch
  - developing / unverified                           -> the long tail
"""
from datetime import datetime, timedelta
from .db import SessionLocal, engine, Base
from .models import User, CandidateProfile, InterviewSession
from .security import hash_password

DEMO_PASSWORD = "demo1234"

# score = (verify, detection, explanation_quality, calibration, coverage_required)
# flags = list of (claim, contradicts) confidently-wrong statements
def _session(cid, item_id, company, domain, level, score, flags, days_ago, transcript):
    verify, detect, expl, calib, cov = score
    ts = datetime.utcnow() - timedelta(days=days_ago)
    fw = [{"claim": c, "contradicts": k} for c, k in flags]
    return InterviewSession(
        id=f"seed_{cid}_{item_id}".replace("-", "").lower()[:40],
        candidate_id=cid, company_id=company, type="practice",
        domain=domain, level=level, proctored=False, status="scored",
        data={
            "item_id": item_id,
            "turns": [{
                "turn_id": "t1", "item_id": item_id, "ts": ts.isoformat(),
                "candidate_input": {"transcript": transcript},
                "scoring": {
                    "verify_score": verify, "detection": detect,
                    "explanation_quality": expl, "calibration": calib,
                    "coverage_required": cov, "fluent_wrongness_count": len(fw),
                },
                "fluent_wrongness_flags": fw,
                "adaptive_followup": {"prompt": ""},
            }],
            "feedback": [],
            "graded_by": "offline",
        },
        created_at=ts, completed_at=ts,
    )


# (email, full_name, [session specs]) — session spec = kwargs for _session minus cid
CANDIDATES = [
    ("ayesha.tariq@demo.pk", "Ayesha Tariq", [
        dict(item_id="D1-1", company="devsinc", domain="core_se", level="engineer",
             score=(91, 95, 88, 92, 100), flags=[], days_ago=2,
             transcript="This is O(n^2): has_pair_with_sum rebuilds a list and does a membership "
                        "scan inside the loop. A set lookup makes it O(n)."),
        dict(item_id="D3-1", company="netsol", domain="database", level="engineer",
             score=(87, 90, 85, 88, 80), flags=[], days_ago=5,
             transcript="The JOIN is on the wrong key, so rows fan out and the SUM double-counts. "
                        "Should join orders.customer_id to customers.id."),
    ]),
    ("bilal.hussain@demo.pk", "Bilal Hussain", [
        dict(item_id="D1-1", company="devsinc", domain="core_se", level="engineer",
             score=(58, 45, 86, 38, 60), days_ago=1,
             flags=[("The function is O(n) because it uses a hash set",
                     "Membership is tested against a list rebuilt each iteration — this is O(n^2).")],
             transcript="Clean, idiomatic code. It runs in O(n) thanks to the hash set, so "
                        "performance is not a concern here and I'd approve it."),
        dict(item_id="D1-3", company="10pearls", domain="core_se", level="associate",
             score=(55, 42, 82, 40, 60),
             flags=[("This will overflow for large inputs in Python",
                     "Python ints are arbitrary-precision; there is no overflow. The real bug is "
                     "an off-by-one on the loop bound.")],
             days_ago=3,
             transcript="The arithmetic risks integer overflow on big inputs, otherwise the logic "
                        "looks correct to me."),
    ]),
    ("fatima.noor@demo.pk", "Fatima Noor", [
        dict(item_id="D1-2", company="arbisoft", domain="core_se", level="engineer",
             score=(82, 88, 80, 84, 100), flags=[], days_ago=4,
             transcript="Mutable default argument: the list persists across calls, so state leaks "
                        "between invocations. Default to None and create inside."),
        dict(item_id="D1-1", company="devsinc", domain="core_se", level="engineer",
             score=(76, 80, 78, 74, 80), flags=[], days_ago=8,
             transcript="Nested membership check in a loop — quadratic. A set would fix it."),
    ]),
    ("zara.sheikh@demo.pk", "Zara Sheikh", [
        dict(item_id="D3-2", company="techlogix", domain="database", level="senior",
             score=(89, 92, 86, 90, 100), flags=[], days_ago=2,
             transcript="Non-aggregated column in SELECT with GROUP BY — the result is "
                        "nondeterministic. Either aggregate it or add it to GROUP BY."),
        dict(item_id="D3-1", company="netsol", domain="database", level="senior",
             score=(84, 86, 83, 85, 80), flags=[], days_ago=6,
             transcript="Wrong join key inflates the totals. Join on customer_id."),
    ]),
    ("usman.ali@demo.pk", "Usman Ali", [
        dict(item_id="D1-3", company="10pearls", domain="core_se", level="associate",
             score=(63, 68, 60, 66, 60), flags=[], days_ago=1,
             transcript="There's an off-by-one in the loop bound; the last element is skipped."),
    ]),
    ("hassan.raza@demo.pk", "Hassan Raza", [
        dict(item_id="D1-1", company="devsinc", domain="core_se", level="associate",
             score=(38, 30, 48, 42, 20), flags=[], days_ago=2,
             transcript="The code looks fine to me, it returns whether a pair exists. Nothing to flag."),
        dict(item_id="D1-2", company="arbisoft", domain="core_se", level="associate",
             score=(41, 35, 50, 44, 40), flags=[], days_ago=7,
             transcript="It appends to a list and returns it. Seems correct."),
    ]),
    ("mehwish.khan@demo.pk", "Mehwish Khan", [
        dict(item_id="D1-1", company="devsinc", domain="core_se", level="senior",
             score=(94, 96, 92, 95, 100), flags=[], days_ago=1,
             transcript="Quadratic membership scan. Hoist into a set for O(n); also note the list "
                        "rebuild each pass is wasted allocation."),
        dict(item_id="D3-2", company="techlogix", domain="database", level="senior",
             score=(90, 93, 88, 91, 100), flags=[], days_ago=4,
             transcript="GROUP BY with a bare non-aggregated column — nondeterministic across engines."),
        dict(item_id="D1-2", company="arbisoft", domain="core_se", level="senior",
             score=(88, 90, 86, 89, 100), flags=[], days_ago=9,
             transcript="Mutable default list — shared across calls. Classic aliasing bug."),
    ]),
]


def seed_candidates() -> dict:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    added_users, added_sessions = 0, 0
    try:
        for email, name, specs in CANDIDATES:
            user = db.query(User).filter(User.email == email).first()
            if user is None:
                user = User(email=email, hashed_password=hash_password(DEMO_PASSWORD),
                            role="candidate", full_name=name)
                db.add(user); db.flush()
                db.add(CandidateProfile(user_id=user.id, is_public=True, data={}))
                added_users += 1
            verifies = []
            for spec in specs:
                sess = _session(user.id, **spec)
                if db.get(InterviewSession, sess.id) is None:
                    db.add(sess); added_sessions += 1
                verifies.append(spec["score"][0])
            # keep the profile's rolling verify current (handy for a candidate self-view)
            prof = db.query(CandidateProfile).filter(CandidateProfile.user_id == user.id).first()
            if prof and verifies:
                prof.verify_score = round(sum(verifies) / len(verifies), 1)
        db.commit()
    finally:
        db.close()
    print(f"seeded {added_users} demo candidates, {added_sessions} sessions "
          f"(login password for all: {DEMO_PASSWORD})")
    return {"candidates": added_users, "sessions": added_sessions}


if __name__ == "__main__":
    seed_candidates()
