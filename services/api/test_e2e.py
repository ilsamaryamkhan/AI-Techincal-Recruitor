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
assert summary["items"] == 5 and summary["companies"] == 5; ok(f"loaded {summary['items']} items / {summary['companies']} companies")

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
assert len(allitems) == 5; ok("list returns 5")
dbitems = c.get("/items?domain=database", headers=H(cand_token)).json()
assert len(dbitems) == 2 and all(i["domain"]=="database" for i in dbitems); ok("filter domain=database -> 2")

print("\n[7] full item is role-gated")
assert c.get("/items/D1-1/full", headers=H(cand_token)).status_code == 403
ok("candidate BLOCKED from /full (403)")
full = c.get("/items/D1-1/full", headers=H(comp_token))
assert full.status_code == 200 and full.json()["fault_label"]["fault_id"] == "EFF-LIST-IN-LOOP"
ok("company user CAN see /full (answer present for grading)")

print("\n" + "="*58)
print("ALL CHECKS PASSED — steps 1-3 work, and the answer never leaks.")
print("="*58)
