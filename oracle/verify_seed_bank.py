"""Verification oracle — proves the seed bank, data-driven.

Runs EVERY item in data/seed_bank.json through the shared oracle engine
(app.oracle.verify_item). An item is admitted only if its injected fault
actually bites: the buggy code must differ from a correct reference
(python_diff), be measurably slower (python_perf), or return a different
result set (sql_diff).

    python oracle/verify_seed_bank.py
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "services", "api"))
from app.oracle import verify_item  # noqa: E402

BANK = os.path.join(ROOT, "data", "seed_bank.json")


def main():
    with open(BANK, encoding="utf-8") as f:
        bank = json.load(f)
    print("=" * 78)
    print(f"VERIFYING SEED BANK — {len(bank['items'])} items")
    print("=" * 78)
    all_ok = True
    for it in bank["items"]:
        r = verify_item(it)
        flag = "VERIFIED (fault bites)" if r["passed"] else "REJECTED (fault does NOT trigger)"
        print(f"[{it['item_id']:6}] {it['domain']:9} {it['level']:9} "
              f"{it['fault_label']['fault_id']:18} -> {flag}")
        print(f"         {r['summary'][:90]}")
        all_ok = all_ok and r["passed"]
    print("=" * 78)
    if all_ok:
        print("ALL ITEMS VERIFIED — every fault bites. Bank is admissible.")
    else:
        print("SOME ITEMS REJECTED — fix them before loading.")
        sys.exit(1)


if __name__ == "__main__":
    main()
