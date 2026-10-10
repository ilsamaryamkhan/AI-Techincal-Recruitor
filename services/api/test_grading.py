"""Step 5 test. Proves grounding + grader, especially the fluent-wrongness catch,
run OFFLINE (no network). Then exercises the LLM path with a mocked Groq client."""
import os, json
os.environ["LLM_API_KEY"] = ""   # force offline path for the deterministic checks
import importlib
from app import config as _cfg; importlib.reload(_cfg)
from app.grading import ground
from app.grading import grader as G
importlib.reload(G)

bank = {it["item_id"]: it for it in json.load(open("../../data/seed_bank.json"))["items"]}
ok = lambda m: print(f"  PASS  {m}")

print("\n[1] grounding sees the truth in the code")
g = ground("python", bank["D1-1"]["artifact"]["files"][0]["content"])
assert g["flags"]["list_membership_in_loop"] is True; ok("D1-1: list-membership-in-loop detected")
g2 = ground("python", bank["D1-2"]["artifact"]["files"][0]["content"])
assert "cart" in g2["flags"]["mutable_default_args"]; ok("D1-2: mutable default arg `cart` detected")
g3 = ground("python", bank["D1-3"]["artifact"]["files"][0]["content"])
assert g3["flags"]["loop_bound_strict_lt"] is True; ok("D1-3: strict `<` loop bound detected")

print("\n[2] THE HEADLINE TEST — fluent wrongness on D1-1 (offline)")
good = "It returns True if any two numbers sum to target. It looks like the O(n) hash-set trick but seen is a list, so membership is O(n) and it's actually O(n^2). Fix: use a set."
wrong = "Clean two-sum. It uses a hash set for O(1) lookups so the whole thing is O(n) time. Looks correct and optimal."
rg = G.grade_submission(bank["D1-1"], good)
rb = G.grade_submission(bank["D1-1"], wrong)
assert rg["scores"]["fluent_wrongness_count"] == 0, rg["scores"]; ok(f"correct answer: no fw flag, verify={rg['scores']['verify_score']}")
assert rb["scores"]["fluent_wrongness_count"] >= 1, rb; ok(f"fluent-wrong answer: fw FLAGGED, verify={rb['scores']['verify_score']}")
assert rg["scores"]["verify_score"] > rb["scores"]["verify_score"]; ok("correct scores higher than fluent-wrong")
assert rg["identified_core_issue"] and not rb["identified_core_issue"]; ok("core issue: caught vs missed")
print(f"        fw flag text: {rb['fluent_wrongness'][0]['contradicts']}")

print("\n[3] other faults grade sensibly (offline)")
r12 = G.grade_submission(bank["D1-2"], "The default cart=[] is created once and shared across calls, so state persists. Use None instead.")
assert r12["identified_core_issue"]; ok(f"D1-2 mutable-default caught, verify={r12['scores']['verify_score']}")
r31 = G.grade_submission(bank["D3-1"], "Joining orders to order_tags is one-to-many so rows fan out and the SUM double counts revenue.")
assert r31["identified_core_issue"]; ok(f"D3-1 join fan-out caught, verify={r31['scores']['verify_score']}")

print("\n[4] decoy calibration — flagging the python 'overflow' decoy on D1-3 costs you")
clean = G.grade_submission(bank["D1-3"], "The loop condition is lo < hi which skips the last element; should be <=. Off-by-one.")
decoyed = G.grade_submission(bank["D1-3"], "The mid = (lo+hi)//2 can overflow. Also lo<hi skips the last element, off-by-one.")
assert decoyed["flagged_decoy"] and not clean["flagged_decoy"]; ok("overflow decoy flagged vs not")
assert clean["scores"]["calibration"] > decoyed["scores"]["calibration"]; ok("clean calibration > decoyed")

print("\n[5] LLM path with a MOCKED Groq response")
import app.grading.llm as llm
llm.LLM_API_KEY = "test"  # make available() true
def fake_chat_json(system, user, max_tokens=1200):
    return {"observations":[{"obs_id":"o1","covered":True},{"obs_id":"o2","covered":True},{"obs_id":"o3","covered":True}],
            "identified_core_issue":True,"fluent_wrongness":[],"flagged_decoy":False,"depth":0.8,"terminology":0.9}
def fake_chat_text(system, user, max_tokens=160): return "What does `in seen` cost on the tenth iteration?"
llm.chat_json, llm.chat_text = fake_chat_json, fake_chat_text
r = G.grade_submission(bank["D1-1"], good)
assert r["graded_by"] == "groq"; ok("LLM path used when key present")
assert r["scores"]["verify_score"] >= 80; ok(f"mocked-LLM grade verify={r['scores']['verify_score']}")
assert "tenth iteration" in r["followup"]; ok("adaptive follow-up came from LLM")

print("\n" + "="*58)
print("STEP 5 GRADING VERIFIED — fluent wrongness is caught, offline and via LLM.")
print("="*58)
