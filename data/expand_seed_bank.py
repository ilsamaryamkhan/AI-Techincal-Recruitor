"""Attach executable `check` blocks to the seed items and add level/domain coverage.

Runs every item (old + new) through the oracle; only writes seed_bank.json if ALL
faults bite. Idempotent — re-running reproduces the same bank.

    python data/expand_seed_bank.py
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "services", "api"))
from app.oracle import verify_item  # noqa: E402

BANK = os.path.join(HERE, "seed_bank.json")

# ---- executable checks for the ORIGINAL five items -------------------------
CHECKS = {
    "D1-1": {
        "kind": "python_perf", "entry": "has_pair_with_sum",
        "reference": "def has_pair_with_sum(nums, target):\n    seen=set()\n    for n in nums:\n        if target-n in seen: return True\n        seen.add(n)\n    return False\n",
        "setup": "args = (list(range(0,40000,2)), 40001)", "min_ratio": 20,
    },
    "D1-2": {
        "kind": "python_diff", "entry": "add_to_cart",
        "reference": "def add_to_cart(item, cart=None):\n    if cart is None: cart=[]\n    cart.append(item); return cart\n",
        "probe": "add_to_cart('apple')\nresult = add_to_cart('banana')",
    },
    "D1-3": {
        "kind": "python_diff", "entry": "binary_search",
        "reference": "def binary_search(arr, target):\n    lo, hi = 0, len(arr)-1\n    while lo <= hi:\n        mid=(lo+hi)//2\n        if arr[mid]==target: return mid\n        elif arr[mid]<target: lo=mid+1\n        else: hi=mid-1\n    return -1\n",
        "probe": "result = binary_search([1,3,5,7,9], 9)",
    },
    "D3-1": {
        "kind": "sql_diff",
        "schema": "CREATE TABLE orders(id INT, customer_id INT, total REAL);"
                  "CREATE TABLE order_tags(order_id INT, tag TEXT);"
                  "INSERT INTO orders VALUES (10,1,5000),(11,1,3000),(12,2,2000);"
                  "INSERT INTO order_tags VALUES (10,'urgent'),(10,'gift'),(10,'fragile'),(11,'urgent');",
        "correct": "SELECT SUM(total) FROM orders",
    },
    "D3-2": {
        "kind": "sql_diff",
        "schema": "CREATE TABLE customers(id INT, name TEXT);"
                  "CREATE TABLE orders(id INT, customer_id INT);"
                  "INSERT INTO customers VALUES (1,'Ayesha'),(2,'Bilal'),(3,'Chaudhry');"
                  "INSERT INTO orders VALUES (10,1),(11,1),(12,2);",
        "correct": "SELECT c.name, COUNT(o.id) FROM customers c LEFT JOIN orders o ON c.id=o.customer_id GROUP BY c.name",
    },
}


def mk(item_id, company, domain, level, lang, prompt, code, fault_id, category, desc,
       obs, decoy, check, roles=None):
    """Assemble a full GeneratedItem with sensible defaults."""
    return {
        "item_id": item_id, "company_id": company, "domain": domain, "level": level,
        "role_tags": roles or ["backend", f"{level}_se"], "mode": "comprehension",
        "language": lang, "blueprint_ref": f"bp_{company}_{domain}_{level}",
        "prompt": prompt,
        "artifact": {"files": [{"path": "solution." + ("sql" if lang == "sql" else "py"),
                                "content": code}], "entrypoint": "solution." + ("sql" if lang == "sql" else "py")},
        "fault_label": {"present": True, "fault_id": fault_id, "category": category,
                        "location": {"file": "solution.py", "line_start": 1, "line_end": 1, "symbol": ""},
                        "description": desc, "severity": "high"},
        "expected_observations": obs,
        "decoys": [decoy],
        "verification": {"method": ["oracle"], "status": "verified", "verified_at": "2026-10-10T00:00:00Z"},
        "check": check,
        "rubric": {"detection_weight": 0.4, "explanation_weight": 0.4, "calibration_weight": 0.2,
                   "concept_mastery_map": {}},
        "irt": {"a": None, "b": None, "calibrated": False},
        "novelty": {"max_similarity_to_public": 0.0, "passed": True},
        "provenance": {"generated_by": "seed_authored", "seed_exemplars": [], "created_at": "2026-10-10T00:00:00Z"},
    }


def obs5(purpose, core, fix, b1, b2):
    return [
        {"obs_id": "o1", "statement": purpose, "required": True, "concept_tags": ["purpose"]},
        {"obs_id": "o2", "statement": core, "required": True, "concept_tags": ["core"]},
        {"obs_id": "o3", "statement": fix, "required": True, "concept_tags": ["fix"]},
        {"obs_id": "o4", "statement": b1, "required": False, "concept_tags": ["detail"]},
        {"obs_id": "o5", "statement": b2, "required": False, "concept_tags": ["detail"]},
    ]


def decoy(looks, fine):
    return {"location": {"file": "solution.py", "line": 1}, "why_it_looks_wrong": looks, "why_its_actually_fine": fine}


NEW = [
    # ---------- core_se ENGINEER ----------
    mk("CE-E1", "systems", "core_se", "engineer", "python",
       "Read this function. Explain what it does, its complexity, and anything you'd flag.",
       "def first_duplicate(nums):\n    seen = []\n    for n in nums:\n        if n in seen:\n            return n\n        seen.append(n)\n    return None\n",
       "EFF-LIST-IN-LOOP", "efficiency",
       "`seen` is a list, so `n in seen` is an O(n) scan inside the loop -> O(n^2) overall.",
       obs5("Returns the first value that appears twice, else None.",
            "Membership test on a list makes it O(n^2); it looks like the O(n) set idiom but isn't.",
            "Fix: make `seen` a set for O(1) membership and O(n) overall.",
            "Space is O(n).", "Returning on the first repeat is correct."),
       decoy("The early return could look like it misses later duplicates.",
             "Returning the first duplicate is exactly the stated behaviour."),
       {"kind": "python_perf", "entry": "first_duplicate",
        "reference": "def first_duplicate(nums):\n    seen=set()\n    for n in nums:\n        if n in seen: return n\n        seen.add(n)\n    return None\n",
        "setup": "args = (list(range(20000)),)", "min_ratio": 20}),

    mk("CE-E2", "folio3", "core_se", "engineer", "python",
       "Read this function. Explain what it computes and whether it is correct.",
       "def sum_first_k(arr, k):\n    total = 0\n    i = 0\n    while i < k - 1:\n        total += arr[i]\n        i += 1\n    return total\n",
       "CORR-OFF-BY-ONE", "correctness",
       "Loop runs while `i < k-1`, so it sums only the first k-1 elements instead of k.",
       obs5("Means to sum the first k elements of arr.",
            "`while i < k - 1` stops one short, summing k-1 elements, not k.",
            "Fix: use `while i < k`.",
            "Concrete case: sum_first_k([1,2,3,4,5], 3) returns 3, should be 6.",
            "Complexity is O(k); the defect is correctness."),
       decoy("Starting `total` at 0 could look like it mishandles empty input.",
             "0 is the correct identity for a sum; empty/zero-k returns 0 fine."),
       {"kind": "python_diff", "entry": "sum_first_k",
        "reference": "def sum_first_k(arr, k):\n    total=0\n    i=0\n    while i < k:\n        total += arr[i]; i += 1\n    return total\n",
        "probe": "result = sum_first_k([1,2,3,4,5], 3)"}),

    # ---------- core_se SENIOR ----------
    mk("CE-S1", "confiz", "core_se", "senior", "python",
       "Read this function. Explain its behaviour, complexity, and anything you'd raise in review.",
       "def dedupe(items):\n    result = []\n    for x in items:\n        if x not in result:\n            result.append(x)\n    return result\n",
       "EFF-LIST-IN-LOOP", "efficiency",
       "`x not in result` scans a list each iteration -> O(n^2); order-preserving dedupe can be O(n) with a set.",
       obs5("Removes duplicates while preserving first-seen order.",
            "`not in result` is an O(n) list scan inside the loop, so it's O(n^2).",
            "Fix: track seen elements in a set for O(1) membership, still appending to the ordered result.",
            "Output order is correct.", "Space is O(n)."),
       decoy("Appending to `result` while iterating looks like mutation-during-iteration.",
             "It iterates `items`, not `result`, so there is no mutation-during-iteration bug."),
       {"kind": "python_perf", "entry": "dedupe",
        "reference": "def dedupe(items):\n    seen=set(); result=[]\n    for x in items:\n        if x not in seen:\n            seen.add(x); result.append(x)\n    return result\n",
        "setup": "args = (list(range(20000)),)", "min_ratio": 20}),

    mk("CE-S2", "venturedive", "core_se", "senior", "python",
       "Read this function. Explain its behaviour across repeated calls and flag any issue.",
       "def tally(key, counts={}):\n    counts[key] = counts.get(key, 0) + 1\n    return counts\n",
       "OOP-MUTABLE-DEFAULT", "design_oop",
       "Default `counts={}` is created once at definition; all default-arg calls share and mutate the same dict.",
       obs5("Increments a per-key counter and returns the dict.",
            "The default {} is shared across calls, so counts persist between independent calls that omit `counts`.",
            "Fix: default to None and create a fresh dict inside when counts is None.",
            "Only bites when the caller omits `counts`.", "Classic mutable-default-argument pitfall, with a dict."),
       decoy("Using `.get(key, 0)` could look like it hides a KeyError.",
             "`.get` with a default is the idiomatic, correct way to initialise a count."),
       {"kind": "python_diff", "entry": "tally",
        "reference": "def tally(key, counts=None):\n    if counts is None: counts={}\n    counts[key]=counts.get(key,0)+1\n    return counts\n",
        "probe": "tally('a')\nresult = tally('b')"}),

    # ---------- database ASSOCIATE ----------
    mk("DB-A1", "i2c", "database", "associate", "sql",
       "This query should total all payments received. Explain the result it actually produces.",
       "SELECT SUM(p.amount)\nFROM payments p\nJOIN line_items l ON p.order_id = l.order_id;\n",
       "DB-WRONG-JOIN", "database",
       "Joining payments (1) to line_items (many) fans each payment out per line item, so SUM(p.amount) over-counts.",
       obs5("Intends to sum every payment's amount.",
            "The join to line_items is one-to-many, duplicating each payment row per line item, inflating the SUM.",
            "Fix: sum from payments alone, or aggregate line_items in a subquery.",
            "Inflation scales with line items per order.", "No GROUP BY is needed for a single total."),
       decoy("A scalar SUM with no GROUP BY can look like a missing grouping.",
             "A single aggregate over the whole set needs no GROUP BY — not the defect."),
       {"kind": "sql_diff",
        "schema": "CREATE TABLE payments(id INT, order_id INT, amount REAL);"
                  "CREATE TABLE line_items(order_id INT, sku TEXT);"
                  "INSERT INTO payments VALUES (1,10,500),(2,11,300);"
                  "INSERT INTO line_items VALUES (10,'a'),(10,'b'),(11,'c');",
        "correct": "SELECT SUM(amount) FROM payments"}),

    mk("DB-A2", "systems", "database", "associate", "sql",
       "This query should list each product with how many times it was ordered, including never-ordered products. Explain what it returns.",
       "SELECT pr.name, COUNT(*)\nFROM products pr\nLEFT JOIN order_lines ol ON pr.id = ol.product_id\nGROUP BY pr.name;\n",
       "DB-GROUPBY-ERR", "database",
       "COUNT(*) counts the NULL-padded LEFT JOIN row for a never-ordered product as 1 instead of 0.",
       obs5("Counts orders per product, keeping products with none.",
            "COUNT(*) counts the single NULL-padded row a LEFT JOIN emits, so a never-ordered product shows 1, not 0.",
            "Fix: COUNT(ol.product_id) (a non-null column from the order side).",
            "The LEFT JOIN and GROUP BY are otherwise fine.", "Shows the COUNT(*) vs COUNT(col) difference under NULLs."),
       decoy("`GROUP BY pr.name` could be flagged if two products share a name.",
             "A fair robustness note, but not the bug under test here."),
       {"kind": "sql_diff",
        "schema": "CREATE TABLE products(id INT, name TEXT);"
                  "CREATE TABLE order_lines(id INT, product_id INT);"
                  "INSERT INTO products VALUES (1,'Pen'),(2,'Mug'),(3,'Lamp');"
                  "INSERT INTO order_lines VALUES (10,1),(11,1),(12,2);",
        "correct": "SELECT pr.name, COUNT(ol.product_id) FROM products pr LEFT JOIN order_lines ol ON pr.id=ol.product_id GROUP BY pr.name"}),

    # ---------- database SENIOR ----------
    mk("DB-S1", "folio3", "database", "senior", "sql",
       "This query should report total invoiced revenue. Explain the result it actually produces.",
       "SELECT SUM(i.amount)\nFROM invoices i\nJOIN invoice_items it ON i.id = it.invoice_id;\n",
       "DB-WRONG-JOIN", "database",
       "Invoices (1) joined to invoice_items (many) fans each invoice out per line, so SUM(i.amount) is inflated.",
       obs5("Intends to total all invoiced revenue.",
            "The one-to-many join duplicates each invoice row per line item, so the SUM over-counts.",
            "Fix: sum from invoices alone, or aggregate invoice_items separately.",
            "An invoice with 3 lines is counted 3x.", "Correct total differs from the inflated one."),
       decoy("Aliasing invoices as `i` could look like a reserved-word clash.",
             "`i` is a fine alias; it is not the defect."),
       {"kind": "sql_diff",
        "schema": "CREATE TABLE invoices(id INT, client_id INT, amount REAL);"
                  "CREATE TABLE invoice_items(invoice_id INT, line TEXT);"
                  "INSERT INTO invoices VALUES (1,7,9000),(2,7,1000);"
                  "INSERT INTO invoice_items VALUES (1,'x'),(1,'y'),(2,'z');",
        "correct": "SELECT SUM(amount) FROM invoices"}),

    mk("DB-S2", "confiz", "database", "senior", "sql",
       "This query should list each team with its member count, including empty teams. Explain what it returns.",
       "SELECT t.name, COUNT(*)\nFROM teams t\nLEFT JOIN members m ON t.id = m.team_id\nGROUP BY t.name;\n",
       "DB-GROUPBY-ERR", "database",
       "COUNT(*) counts the NULL-padded LEFT JOIN row for an empty team as 1 instead of 0.",
       obs5("Counts members per team, keeping empty teams.",
            "COUNT(*) counts the NULL-padded row for an empty team as 1 rather than 0.",
            "Fix: COUNT(m.id) so NULLs from the members side are not counted.",
            "Only the COUNT argument is wrong.", "Demonstrates COUNT(*) vs COUNT(col) under NULLs."),
       decoy("The LEFT JOIN direction could look reversed.",
             "teams LEFT JOIN members is correct for keeping every team."),
       {"kind": "sql_diff",
        "schema": "CREATE TABLE teams(id INT, name TEXT);"
                  "CREATE TABLE members(id INT, team_id INT);"
                  "INSERT INTO teams VALUES (1,'Alpha'),(2,'Beta'),(3,'Gamma');"
                  "INSERT INTO members VALUES (10,1),(11,1),(12,2);",
        "correct": "SELECT t.name, COUNT(m.id) FROM teams t LEFT JOIN members m ON t.id=m.team_id GROUP BY t.name"}),
]


def main():
    with open(BANK, encoding="utf-8") as f:
        bank = json.load(f)

    by_id = {it["item_id"]: it for it in bank["items"]}
    for iid, chk in CHECKS.items():
        if iid in by_id:
            by_id[iid]["check"] = chk
    existing_ids = set(by_id)
    for it in NEW:
        if it["item_id"] not in existing_ids:
            bank["items"].append(it)

    # verify EVERY item's fault bites before writing
    print("Verifying all items through the oracle:")
    all_ok = True
    for it in bank["items"]:
        r = verify_item(it)
        flag = "VERIFIED" if r["passed"] else "REJECTED"
        print(f"  [{it['item_id']:6}] {it['domain']:9} {it['level']:9} {it['fault_label']['fault_id']:18} {flag}  {r['summary'][:70]}")
        all_ok = all_ok and r["passed"]
    if not all_ok:
        print("\nSOME ITEMS FAILED — not writing seed_bank.json"); sys.exit(1)

    bank["domains"] = ["core_se", "database"]
    with open(BANK, "w", encoding="utf-8") as f:
        json.dump(bank, f, indent=2, ensure_ascii=False)
    # coverage report
    from collections import Counter
    cov = Counter((it["domain"], it["level"]) for it in bank["items"])
    print(f"\nWROTE {len(bank['items'])} items. Coverage:")
    for (d, lv), n in sorted(cov.items()):
        print(f"  {d:9} {lv:9} : {n}")


if __name__ == "__main__":
    main()
