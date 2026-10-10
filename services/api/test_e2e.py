"""End-to-end smoke test for steps 1-3. Uses FastAPI TestClient (no server needed).
Proves: register -> login -> seed -> fetch, AND that no answer field ever leaks."""
import os, tempfile
# fresh throwaway DB so the test is repeatable
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.gettempdir()}/asaanhire_test.db"
os.environ["SEED_BANK_PATH"] = "../../data/seed_bank.json"
db_file = os.environ["DATABASE_URL"].replace("sqlite:///", "")
if os.path.exists(db_file): os.remove(db_file)

from fastapi.testclient import TestClient
from app.main import app
from app.seed_loader import load_seed_bank
from app.schemas import ANSWER_FIELDS

# context-manager form triggers the lifespan handler (creates tables), same as uvicorn does
client_cm = TestClient(app)
c = client_cm.__enter__()
ok = lambda label: print(f"  PASS  {label}")

print("\n[1] health")
assert c.get("/health").json()["status"] == "ok"; ok("api up, title asaanHire")

print("\n[2] register candidate + company user")
r = c.post("/auth/register", json={"email":"ayesha@test.pk","password":"pw123456","role":"candidate","full_name":"Ayesha"})
assert r.status_code == 201, r.text; cand_token = r.json()["access_token"]; ok("candidate registered")
r = c.post("/auth/register", json={"email":"hr@devsinc.com","password":"pw123456","role":"company","company_id":"devsinc"})
assert r.status_code == 201, r.text; comp_token = r.json()["access_token"]; ok("company user registered")
assert c.post("/auth/register", json={"email":"ayesha@test.pk","password":"x","role":"candidate"}).status_code == 409
ok("duplicate email rejected (409)")

print("\n[3] login + me")
r = c.post("/auth/login", json={"email":"ayesha@test.pk","password":"pw123456"})
assert r.status_code == 200, r.text; cand_token = r.json()["access_token"]; ok("login returns token")
assert c.post("/auth/login", json={"email":"ayesha@test.pk","password":"WRONG"}).status_code == 401
ok("wrong password rejected (401)")
H = lambda t: {"Authorization": f"Bearer {t}"}
me = c.get("/auth/me", headers=H(cand_token)).json()
assert me["role"] == "candidate" and me["email"] == "ayesha@test.pk"; ok("GET /auth/me works")
assert c.get("/auth/me").status_code == 401; ok("no token -> 401")

print("\n[4] seed the bank")
summary = load_seed_bank()
assert summary["items"] == 13 and summary["companies"] == 10; ok(f"loaded {summary['items']} items / {summary['companies']} companies")
companies = c.get("/companies").json()
assert len(companies) == 10 and any(x["id"] == "venturedive" for x in companies); ok("GET /companies returns all 10 (public, for signup)")

print("\n[5] candidate item view — THE LEAK TEST")
r = c.get("/items/D1-1", headers=H(cand_token))
assert r.status_code == 200, r.text; item = r.json()
assert item["item_id"] == "D1-1" and "artifact" in item; ok("candidate can fetch item + its code")
leaked = ANSWER_FIELDS & set(item.keys())
assert not leaked, f"LEAKED ANSWER FIELDS: {leaked}"; ok("no fault_label/verification/decoys/expected_observations in payload")
# also make sure the actual answer text isn't hiding somewhere in the serialized blob
blob = str(item).lower()
for needle in ["o(n^2)", "fault_bites", "verified", "why_its_actually_fine", "expected_observations"]:
    assert needle not in blob, f"answer text leaked: {needle!r}"
ok("answer text absent from the serialized candidate payload")

print("\n[6] list + filter")
allitems = c.get("/items", headers=H(cand_token)).json()
assert len(allitems) == 13; ok("list returns 13")
dbitems = c.get("/items?domain=database", headers=H(cand_token)).json()
assert len(dbitems) == 6 and all(i["domain"]=="database" for i in dbitems); ok("filter domain=database -> 6")
senior = c.get("/items?domain=core_se&level=senior", headers=H(cand_token)).json()
assert len(senior) >= 2; ok(f"core_se senior coverage -> {len(senior)} items")

print("\n[7] full item is role-gated")
assert c.get("/items/D1-1/full", headers=H(cand_token)).status_code == 403
ok("candidate BLOCKED from /full (403)")
full = c.get("/items/D1-1/full", headers=H(comp_token))
assert full.status_code == 200 and full.json()["fault_label"]["fault_id"] == "EFF-LIST-IN-LOOP"
ok("company user CAN see /full (answer present for grading)")

print("\n[8] recruiter dashboard — pool, filters, role gating")
from app.seed_candidates import seed_candidates
seed_candidates()
r = c.post("/auth/register", json={"email":"rec@devsinc.com","password":"pw123456","role":"recruiter","company_id":"devsinc"})
assert r.status_code == 201, r.text; rec_token = r.json()["access_token"]; ok("recruiter registered")
assert c.get("/recruiter/candidates", headers=H(cand_token)).status_code == 403
ok("candidate BLOCKED from /recruiter (403)")
stats = c.get("/recruiter/stats", headers=H(rec_token)).json()
assert stats["candidates"] == 7 and stats["verified"] >= 3; ok(f"stats: {stats['candidates']} candidates, {stats['verified']} verified")
assert stats["fluent_wrongness_flagged"] >= 1; ok("pool surfaces confidently-wrong candidate(s)")
pool = c.get("/recruiter/candidates", headers=H(rec_token)).json()
scores = [p["verify_score"] for p in pool]
assert scores == sorted(scores, reverse=True); ok("default sort = verify desc")
byfluent = c.get("/recruiter/candidates?sort=fluent", headers=H(rec_token)).json()
assert byfluent[0]["name"] == "Bilal Hussain" and byfluent[0]["fluent_wrongness_total"] >= 2
ok("sort=fluent surfaces the fluent-but-wrong candidate first")
dbonly = c.get("/recruiter/candidates?domain=database", headers=H(rec_token)).json()
assert dbonly and all("database" in p["domains"] for p in dbonly); ok("filter domain=database works")
verified = c.get("/recruiter/candidates?credential=verified", headers=H(rec_token)).json()
assert verified and all(p["verified"] for p in verified); ok("filter credential=verified works")
bilal_id = next(p["user_id"] for p in pool if p["name"] == "Bilal Hussain")
detail = c.get(f"/recruiter/candidates/{bilal_id}", headers=H(rec_token)).json()
assert detail["credential"] == "developing" and len(detail["fluent_wrongness_record"]) >= 2
ok("candidate detail carries the confidently-wrong record")
assert c.get(f"/recruiter/candidates/{bilal_id}", headers=H(cand_token)).status_code == 403
ok("candidate BLOCKED from reading another profile (403)")
assert c.get("/recruiter/candidates/999999", headers=H(rec_token)).status_code == 404
ok("unknown candidate -> 404")

print("\n[9] live interview loop — adaptive, no mid-interview leak, flows to pool")
r = c.post("/auth/register", json={"email":"imran@test.pk","password":"pw123456","role":"candidate","full_name":"Imran Verify"})
assert r.status_code == 201, r.text; iv_token = r.json()["access_token"]
s = c.post("/interview/start", json={}, headers=H(iv_token)).json()
sid = s["session_id"]
assert s["total"] == 3 and s["stage"] == "main" and "artifact" in s["item"]; ok("interview starts: 3 items, first served")
assert not (ANSWER_FIELDS & set(s["item"].keys())); ok("served item is answer-stripped")
assert c.post("/interview/start", json={}, headers=H(comp_token)).status_code == 403; ok("company/recruiter can't take an interview (403)")
def iv_answer(txt): return c.post(f"/interview/{sid}/answer", json={"transcript":txt}, headers=H(iv_token)).json()
r1 = iv_answer("Clean code, it's O(n) via a hash set so performance is fine.")
assert r1["stage"] == "followup" and r1.get("followup"); ok("main answer -> adaptive follow-up returned")
assert "verify_score" not in r1 and "scores" not in r1; ok("NO score leaks to candidate mid-interview")
assert iv_answer("Actually the list makes it O(n^2).")["index"] == 1; ok("follow-up answered -> advanced to item 2")
iv_answer("I'd check the boundaries."); iv_answer("Off-by-one skips the last element.")
iv_answer("Wrong join key inflates totals."); fin = iv_answer("Join on customer_id.")
assert fin.get("done") and fin["summary"]["items"] == 3; ok(f"interview finishes with summary (verify {fin['summary']['verify_score']})")
assert c.post(f"/interview/{sid}/answer", json={"transcript":"x"}, headers=H(iv_token)).status_code == 400; ok("finished interview rejects more answers")
pool2 = c.get("/recruiter/candidates", headers=H(rec_token)).json()
imran = next((p for p in pool2 if p["name"] == "Imran Verify"), None)
assert imran and imran["items_attempted"] == 3 and imran["fluent_wrongness_total"] >= 1
ok("interview candidate flows into recruiter pool (3 items, confidently-wrong flagged)")

print("\n[10] proctoring — summary stored, integrity surfaced to recruiter")
pr = c.post(f"/interview/{sid}/proctor", json={
    "integrity_confidence": 0.6, "risk_score": 40, "camera_available": True,
    "flagged_segments": [{"t": 20, "type": "tab_hidden", "severity": 18, "note": "Left the interview tab"},
                         {"t": 55, "type": "multiple_faces", "severity": 30, "note": "2 people in frame"}],
    "counts": {"tab_hidden": 1, "multiple_faces": 1}, "risk_timeseries": [{"t": 0, "risk": 0}],
}, headers=H(iv_token))
assert pr.status_code == 200 and pr.json()["proctored"]; ok("proctoring summary accepted, session marked proctored")
# a different candidate can't post proctoring to someone else's session
assert c.post(f"/interview/{sid}/proctor", json={}, headers=H(cand_token)).status_code == 403
ok("proctoring is owner-gated (403 for another candidate)")
det = c.get(f"/recruiter/candidates/{imran['user_id']}", headers=H(rec_token)).json()
assert det["proctoring"] and round(det["proctoring"]["integrity_confidence"] * 100) == 60
assert len(det["proctoring"]["flagged_segments"]) == 2; ok("recruiter detail shows integrity 60 with 2 flagged moments")

print("\n[11] company test authoring — oracle gate, publish, leak-safe")
good = {"domain":"core_se","level":"engineer","language":"python",
        "prompt":"Read this function and explain whether it is correct for all inputs.",
        "code":"def last(a):\n    return a[len(a)]\n","fault_id":"CORR-INDEX",
        "fault_description":"Indexing at len(a) is past the end; should be len(a)-1.",
        "observations":["Returns the last element.","a[len(a)] is out of range -> IndexError.","Fix: a[-1]."],
        "decoy_looks_wrong":"","decoy_actually_fine":"",
        "check":{"kind":"python_diff","reference":"def last(a):\n    return a[len(a)-1]\n","probe":"result = last([1,2,3])"}}
v = c.post("/company/items/verify", json=good, headers=H(comp_token)).json()
assert v["passed"]; ok("oracle verify passes a biting test")
cr = c.post("/company/items", json=good, headers=H(comp_token))
assert cr.status_code == 201, cr.text; new_id = cr.json()["item_id"]; ok(f"published company item {new_id}")
cview = c.get(f"/items/{new_id}", headers=H(cand_token)).json()
assert not (ANSWER_FIELDS & set(cview.keys())); ok("company item reaches candidate answer-stripped (incl. `check`)")
bad = dict(good); bad["check"] = {"kind":"python_diff","reference":"def last(a):\n    return a[len(a)]\n","probe":"result = last([1,2,3])"}
assert c.post("/company/items", json=bad, headers=H(comp_token)).status_code == 422; ok("oracle REJECTS a non-biting test (422)")
assert c.post("/company/items/verify", json=good, headers=H(cand_token)).status_code == 403; ok("candidate can't author (403)")
assert any(m["item_id"] == new_id for m in c.get("/company/items", headers=H(comp_token)).json()); ok("company sees its own bank")

print("\n" + "="*58)
print("ALL CHECKS PASSED — steps 1-9 work: answer never leaks,")
print("adaptive proctored interviews, and oracle-gated company tests.")
print("="*58)
