"""The verification oracle — data-driven.

An item is only admitted to the bank (ours or a company's) if its injected fault
actually *bites*: the buggy code must behave differently from a correct reference.
This is what stops a broken or trivial "test" from going live.

Each item carries a server-only `check` block describing how to prove the fault:

  python_diff : run a probe against the candidate code and against a reference fix;
                the fault bites iff the two produce different results.
  python_perf : the candidate is functionally correct but slower; the fault bites
                iff candidate_time / reference_time >= min_ratio (e.g. O(n^2) vs O(n)).
  sql_diff    : run the candidate SQL and a correct SQL over a seeded SQLite db;
                the fault bites iff the result sets differ.

Python runs in a short-lived, isolated subprocess (CPU + memory capped on Linux).
This is demo-grade sandboxing — a production deployment would use a real sandbox
(gVisor/Firecracker/container) before executing third-party code.
"""
from __future__ import annotations
import json
import subprocess
import sqlite3
import sys
from typing import Any

TIMEOUT_S = 6

# runner executed in a fresh, isolated interpreter; reads a JSON job on stdin.
_RUNNER = r'''
import json, sys, time
try:
    import resource  # Unix only; absent on Windows — limits are best-effort
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_AS, (512*1024*1024, 512*1024*1024))
except Exception:
    pass
job = json.load(sys.stdin)
ns = {}
try:
    exec(job["code"], ns)
    if job["mode"] == "diff":
        exec(job["probe"], ns)
        print(json.dumps({"ok": True, "result": repr(ns.get("result"))}))
    else:  # perf
        exec(job["setup"], ns)
        fn = ns[job["entry"]]
        args = ns["args"]
        out = fn(*args)
        t0 = time.perf_counter(); fn(*args); dt = time.perf_counter() - t0
        print(json.dumps({"ok": True, "time": dt, "out": repr(out)}))
except Exception as e:
    print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}))
'''


def _run_python(code: str, mode: str, *, probe: str = "", setup: str = "", entry: str = "") -> dict:
    job = json.dumps({"code": code, "mode": mode, "probe": probe, "setup": setup, "entry": entry})
    try:
        p = subprocess.run(
            [sys.executable, "-I", "-S", "-c", _RUNNER],
            input=job, capture_output=True, text=True, timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timed out"}
    if p.returncode != 0 and not p.stdout.strip():
        return {"ok": False, "error": (p.stderr or "runner crashed").strip()[:200]}
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return {"ok": False, "error": f"bad runner output: {p.stdout[:120]}"}


def _check_python_diff(code: str, chk: dict) -> dict:
    ref = chk["reference"]; probe = chk["probe"]
    cand = _run_python(code, "diff", probe=probe)
    good = _run_python(ref, "diff", probe=probe)
    # the reference (author's fix) MUST run cleanly — otherwise the test is broken
    if not good.get("ok"):
        return {"name": "python_diff", "ok": False, "detail": f"reference code errored: {good.get('error')}"}
    # an exception in the candidate is a valid fault outcome (crash vs correct return)
    cand_out = cand["result"] if cand.get("ok") else f"ERROR {cand.get('error')}"
    good_out = good["result"]
    bites = cand_out != good_out
    return {"name": "python_diff", "ok": bites,
            "detail": (f"fault bites: candidate={cand_out} vs correct={good_out}" if bites
                       else f"fault does NOT trigger — both return {good_out}")}


def _check_python_perf(code: str, chk: dict) -> dict:
    ref = chk["reference"]; setup = chk["setup"]; entry = chk["entry"]; min_ratio = chk.get("min_ratio", 20)
    cand = _run_python(code, "perf", setup=setup, entry=entry)
    good = _run_python(ref, "perf", setup=setup, entry=entry)
    if not cand.get("ok"):
        return {"name": "python_perf", "ok": False, "detail": f"candidate code errored: {cand.get('error')}"}
    if not good.get("ok"):
        return {"name": "python_perf", "ok": False, "detail": f"reference code errored: {good.get('error')}"}
    if cand["out"] != good["out"]:
        return {"name": "python_perf", "ok": False,
                "detail": f"not functionally equivalent (candidate {cand['out']} vs {good['out']})"}
    ratio = cand["time"] / max(good["time"], 1e-6)
    bites = ratio >= min_ratio
    return {"name": "python_perf", "ok": bites,
            "detail": f"ratio {ratio:.0f}x (threshold {min_ratio}x), candidate {cand['time']*1000:.1f}ms vs {good['time']*1000:.1f}ms"}


def _check_sql_diff(code: str, chk: dict) -> dict:
    schema = chk["schema"]; correct = chk["correct"]
    try:
        db = sqlite3.connect(":memory:")
        db.executescript(schema)
        faulty = db.execute(code).fetchall()
        good = db.execute(correct).fetchall()
        db.close()
    except Exception as e:
        return {"name": "sql_diff", "ok": False, "detail": f"SQL errored: {type(e).__name__}: {e}"}
    bites = faulty != good
    return {"name": "sql_diff", "ok": bites,
            "detail": (f"fault bites: faulty={faulty} vs correct={good}" if bites
                       else f"fault does NOT trigger — both return {faulty}")}


def verify_item(item: dict) -> dict:
    """Run an item's check. Returns {passed, checks:[...], summary}."""
    chk = item.get("check")
    if not chk:
        return {"passed": False, "checks": [], "summary": "no executable check attached"}
    code = item["artifact"]["files"][0]["content"]
    kind = chk.get("kind")
    if kind == "python_diff":   result = _check_python_diff(code, chk)
    elif kind == "python_perf": result = _check_python_perf(code, chk)
    elif kind == "sql_diff":    result = _check_sql_diff(code, chk)
    else:
        return {"passed": False, "checks": [], "summary": f"unknown check kind: {kind}"}
    return {"passed": result["ok"], "checks": [result], "summary": result["detail"]}
