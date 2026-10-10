"""Generate a comprehension item from a plain document.

The recruiter uploads a document (a job description, a topic list, interview notes —
ordinary prose, NOT code) and says which position/level/domain they're hiring for.
We turn that into one verified comprehension item: AI-style code with exactly one
real, subtle fault matched to the role, plus the reference fix the oracle runs.

Two paths, same guarantee — the returned draft's fault always BITES:
  LLM path (Groq): writes a novel item grounded in the document. Validated, then
                   run through the oracle; only a biting draft is returned.
  Offline path   : if the LLM is unavailable or its draft doesn't bite, fall back
                   to a curated template matched to (domain, level), personalised
                   to the position. Every template is oracle-verified here, so the
                   demo never hard-fails.

The returned draft is exactly the shape the authoring form + /company/items expect,
so the recruiter reviews it and publishes through the normal (re-verifying) flow.
"""
from __future__ import annotations
from .grading.llm import chat_json, available as llm_available
from .oracle import verify_item

# ----------------------------------------------------------------------------- text extraction
def extract_text(filename: str, raw: bytes) -> str:
    """Pull plain text out of an uploaded document. txt/md native; pdf/docx if libs present."""
    name = (filename or "").lower()
    if name.endswith((".txt", ".md", ".markdown", ".rtf", ".csv")) or not name:
        try:
            return raw.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    if name.endswith(".pdf"):
        try:
            import io, pypdf
            r = pypdf.PdfReader(io.BytesIO(raw))
            return "\n".join((p.extract_text() or "") for p in r.pages)
        except Exception:
            return raw.decode("utf-8", errors="ignore")
    if name.endswith((".docx",)):
        try:
            import io, docx
            d = docx.Document(io.BytesIO(raw))
            return "\n".join(p.text for p in d.paragraphs)
        except Exception:
            return raw.decode("utf-8", errors="ignore")
    return raw.decode("utf-8", errors="ignore")


# ----------------------------------------------------------------------------- offline templates
# Each is a complete, oracle-verified draft. `_tag` is woven into fault_id so a
# generated item is distinguishable from the seed bank. Checks are deterministic
# (python_diff / sql_diff — no timing), so they bite reliably on any machine.
TEMPLATES: dict[tuple[str, str], dict] = {
    ("core_se", "associate"): {
        "language": "python", "_tag": "AVG",
        "prompt": "Read this function. Explain what it computes and whether it is correct for all inputs.",
        "code": "def average(xs):\n    total = 0\n    for x in xs:\n        total += x\n    return total / (len(xs) + 1)\n",
        "fault_id": "CORR-AVG-DENOM",
        "fault_description": "The mean divides by len(xs)+1 instead of len(xs), so every result is too small.",
        "observations": [
            "Sums the list correctly, then divides to get a mean.",
            "The denominator is len(xs)+1, which is one too many — the average is understated.",
            "Fix: divide by len(xs) (and guard the empty list).",
        ],
        "decoy_looks_wrong": "Accumulating in a Python loop looks naive.",
        "decoy_actually_fine": "A simple accumulate loop is perfectly correct; the bug is only the denominator.",
        "check": {"kind": "python_diff",
                  "reference": "def average(xs):\n    return sum(xs) / len(xs)\n",
                  "probe": "result = average([2, 4, 6])"},
    },
    ("core_se", "engineer"): {
        "language": "python", "_tag": "MUTDEF",
        "prompt": "Read this function. Explain whether repeated calls behave as a caller would expect.",
        "code": "def collect(x, bucket=[]):\n    bucket.append(x)\n    return bucket\n",
        "fault_id": "OOP-MUTABLE-DEFAULT",
        "fault_description": "The default list is created once and shared across calls, so state leaks between invocations.",
        "observations": [
            "Appends x to bucket and returns it.",
            "The default [] is evaluated once at definition, so separate calls share one list.",
            "Fix: default to None and create a fresh list inside the function.",
        ],
        "decoy_looks_wrong": "Mutating the argument in place looks risky.",
        "decoy_actually_fine": "In-place append is fine when the caller passes their own list; the trap is only the shared default.",
        "check": {"kind": "python_diff",
                  "reference": "def collect(x, bucket=None):\n    if bucket is None:\n        bucket = []\n    bucket.append(x)\n    return bucket\n",
                  "probe": "result = (collect(1), collect(2))"},
    },
    ("core_se", "senior"): {
        "language": "python", "_tag": "MEDIAN",
        "prompt": "Read this function. Explain whether it returns the correct median for every input.",
        "code": "def median(xs):\n    xs = sorted(xs)\n    n = len(xs)\n    return xs[n // 2]\n",
        "fault_id": "CORR-MEDIAN-EVEN",
        "fault_description": "For an even-length list it returns the upper-middle element instead of averaging the two middle values.",
        "observations": [
            "Sorts the input and indexes the middle element.",
            "For even n there is no single middle; the median should average xs[n//2-1] and xs[n//2].",
            "As written it returns the upper of the two middles, so even-length inputs are wrong.",
        ],
        "decoy_looks_wrong": "Re-sorting inside the function looks wasteful.",
        "decoy_actually_fine": "Sorting is required to find a median; cost is not the issue here.",
        "check": {"kind": "python_diff",
                  "reference": "def median(xs):\n    xs = sorted(xs)\n    n = len(xs)\n    if n % 2:\n        return xs[n // 2]\n    return (xs[n // 2 - 1] + xs[n // 2]) / 2\n",
                  "probe": "result = median([1, 2, 3, 4])"},
    },
    ("database", "associate"): {
        "language": "sql", "_tag": "JOIN",
        "prompt": "Read this query. It should list every customer with how many orders they have placed. Is it correct?",
        "code": "SELECT c.name, COUNT(o.id) AS orders\nFROM customers c\nJOIN orders o ON o.customer_id = c.id\nGROUP BY c.id;",
        "fault_id": "DB-INNER-JOIN-DROPS",
        "fault_description": "An INNER JOIN drops customers who have no orders; they should appear with a count of 0.",
        "observations": [
            "Groups orders by customer and counts them.",
            "INNER JOIN excludes customers with zero orders entirely, so the list is incomplete.",
            "Fix: use LEFT JOIN so every customer appears, counting 0 where there are none.",
        ],
        "decoy_looks_wrong": "COUNT(o.id) instead of COUNT(*) looks suspicious.",
        "decoy_actually_fine": "COUNT(o.id) is actually the right choice with a LEFT JOIN — it counts 0 for unmatched rows.",
        "check": {"kind": "sql_diff",
                  "schema": ("CREATE TABLE customers(id INTEGER, name TEXT);"
                             "CREATE TABLE orders(id INTEGER, customer_id INTEGER);"
                             "INSERT INTO customers VALUES (1,'Ayesha'),(2,'Bilal'),(3,'Zara');"
                             "INSERT INTO orders VALUES (10,1),(11,1),(12,2);"),
                  "correct": "SELECT c.name, COUNT(o.id) AS orders FROM customers c "
                             "LEFT JOIN orders o ON o.customer_id = c.id GROUP BY c.id;"},
    },
    ("database", "engineer"): {
        "language": "sql", "_tag": "DISTINCT",
        "prompt": "Read this query. It should report how many DISTINCT products each category has sold. Is it correct?",
        "code": "SELECT category, COUNT(product) AS products\nFROM sales\nGROUP BY category;",
        "fault_id": "DB-COUNT-NOT-DISTINCT",
        "fault_description": "COUNT(product) counts every sale row, not distinct products, so repeat sales inflate the number.",
        "observations": [
            "Groups sales by category and counts product rows.",
            "COUNT(product) counts rows, not unique products; a product sold twice is counted twice.",
            "Fix: COUNT(DISTINCT product).",
        ],
        "decoy_looks_wrong": "Grouping only by category looks too coarse.",
        "decoy_actually_fine": "Grouping by category is exactly what 'per category' asks for; the bug is the missing DISTINCT.",
        "check": {"kind": "sql_diff",
                  "schema": ("CREATE TABLE sales(category TEXT, product TEXT);"
                             "INSERT INTO sales VALUES ('fruit','apple'),('fruit','apple'),"
                             "('fruit','pear'),('veg','carrot');"),
                  "correct": "SELECT category, COUNT(DISTINCT product) AS products FROM sales GROUP BY category;"},
    },
    ("database", "senior"): {
        "language": "sql", "_tag": "NOTIN",
        "prompt": "Read this query. It should list employees who manage no one. Does it return the right rows?",
        "code": "SELECT name\nFROM emp\nWHERE id NOT IN (SELECT manager_id FROM emp);",
        "fault_id": "DB-NOT-IN-NULL",
        "fault_description": "manager_id contains NULLs, and NOT IN against a set containing NULL yields no rows at all.",
        "observations": [
            "Tries to find ids that never appear as a manager_id.",
            "Because the subquery returns a NULL, the NOT IN comparison is never true, so the result is empty.",
            "Fix: exclude NULLs in the subquery (WHERE manager_id IS NOT NULL) or use NOT EXISTS.",
        ],
        "decoy_looks_wrong": "A correlated subquery would look more deliberate.",
        "decoy_actually_fine": "A plain subquery is fine here; the real trap is NULL handling in NOT IN.",
        "check": {"kind": "sql_diff",
                  "schema": ("CREATE TABLE emp(id INTEGER, name TEXT, manager_id INTEGER);"
                             "INSERT INTO emp VALUES (1,'CEO',NULL),(2,'Lead',1),(3,'Dev',2);"),
                  "correct": "SELECT name FROM emp WHERE id NOT IN "
                             "(SELECT manager_id FROM emp WHERE manager_id IS NOT NULL);"},
    },
}

_LEVEL_FALLBACK = {"associate": ["associate", "engineer", "senior"],
                   "engineer": ["engineer", "senior", "associate"],
                   "senior": ["senior", "engineer", "associate"]}


def _pick_template(domain: str, level: str) -> dict:
    dom = domain if any(d == domain for d, _ in TEMPLATES) else "core_se"
    for lv in _LEVEL_FALLBACK.get(level, ["associate", "engineer", "senior"]):
        if (dom, lv) in TEMPLATES:
            return TEMPLATES[(dom, lv)]
    return TEMPLATES[("core_se", "associate")]


def _draft_from_template(t: dict, domain: str, level: str, position: str) -> dict:
    """Shape a template into an ItemDraft dict, personalised to the role."""
    role = (position or "").strip()
    prompt = t["prompt"]
    if role:
        prompt = f"For the {role} role: {prompt}"
    return {
        "domain": domain if (domain, level) in TEMPLATES or domain in {d for d, _ in TEMPLATES} else "core_se",
        "level": level, "language": t["language"], "prompt": prompt, "code": t["code"],
        "fault_id": t["fault_id"], "fault_description": t["fault_description"],
        "observations": list(t["observations"]),
        "decoy_looks_wrong": t.get("decoy_looks_wrong", ""),
        "decoy_actually_fine": t.get("decoy_actually_fine", ""),
        "check": dict(t["check"]),
    }


# ----------------------------------------------------------------------------- LLM path
_SYS = (
    "You are an assessment author for a code-comprehension hiring platform. "
    "Given a role and a source document, you write ONE short code artifact that an AI might "
    "plausibly produce, containing EXACTLY ONE real, subtle fault appropriate to the role's "
    "domain and seniority. The candidate will read the code and explain whether it is correct. "
    "You must also give the corrected reference code so an automated oracle can prove the fault "
    "changes behaviour. Return a single JSON object and nothing else."
)


def _user_prompt(domain, level, language, position, source_text) -> str:
    schema = (
        '{"code": "<buggy code, '
        + language
        + '>", "fault_id": "<SHORT-SLUG>", "fault_description": "<one sentence>", '
        '"observations": ["<what a strong answer notes>", "...", "... (at least 3)"], '
        '"decoy_looks_wrong": "<a part that looks wrong but is fine>", '
        '"decoy_actually_fine": "<why it is fine>", "check": '
    )
    if language == "sql":
        schema += ('{"kind": "sql_diff", "schema": "<CREATE + INSERT seed so the fault shows>", '
                   '"correct": "<the fixed query>"}}')
        rule = ("The fault must make the buggy query return a DIFFERENT result set than the correct query "
                "on your seed data.")
    else:
        schema += ('{"kind": "python_diff", "reference": "<the fixed function, same name/signature>", '
                   '"probe": "result = <call the function>"}}')
        rule = ("The probe must set a variable named result by calling the function. The buggy code and the "
                "reference must return DIFFERENT results (or the buggy one must raise) for that probe.")
    return (
        f"Role / position: {position or 'software engineer'}\n"
        f"Domain: {domain}\nSeniority: {level}\nLanguage: {language}\n\n"
        f"Source document (use its topics to theme the code; do NOT copy it verbatim):\n"
        f"\"\"\"\n{(source_text or '').strip()[:2500]}\n\"\"\"\n\n"
        f"Write a {level}-level fault. {rule}\n"
        f"Return JSON exactly in this shape:\n{schema}"
    )


def _valid_shape(d: dict, language: str) -> bool:
    if not isinstance(d, dict):
        return False
    for k in ("code", "fault_id", "fault_description", "observations", "check"):
        if k not in d:
            return False
    if not isinstance(d["observations"], list) or len([o for o in d["observations"] if str(o).strip()]) < 3:
        return False
    chk = d["check"]
    if not isinstance(chk, dict):
        return False
    if language == "sql":
        return chk.get("kind") == "sql_diff" and bool(chk.get("schema")) and bool(chk.get("correct"))
    return chk.get("kind") == "python_diff" and bool(chk.get("reference")) and bool(chk.get("probe"))


def _bites(draft: dict) -> bool:
    """Run the oracle on a draft without persisting — same check as publish."""
    payload = {"artifact": {"files": [{"path": "solution", "content": draft["code"]}]},
               "check": draft["check"]}
    try:
        return verify_item(payload)["passed"]
    except Exception:
        return False


def _llm_draft(domain, level, language, position, source_text) -> dict | None:
    if not llm_available():
        return None
    for _ in range(2):  # a couple of attempts; each is oracle-gated
        raw = chat_json(_SYS, _user_prompt(domain, level, language, position, source_text), max_tokens=1400)
        if not raw or not _valid_shape(raw, language):
            continue
        draft = {
            "domain": domain, "level": level, "language": language,
            "prompt": raw.get("prompt") or f"For the {position or 'role'}: read this code and explain whether it is correct.",
            "code": raw["code"], "fault_id": str(raw["fault_id"])[:40],
            "fault_description": raw["fault_description"],
            "observations": [str(o) for o in raw["observations"] if str(o).strip()][:6],
            "decoy_looks_wrong": raw.get("decoy_looks_wrong", ""),
            "decoy_actually_fine": raw.get("decoy_actually_fine", ""),
            "check": raw["check"],
        }
        if _bites(draft):
            return draft
    return None


# ----------------------------------------------------------------------------- public entry
def generate_item(domain: str, level: str, language: str, position: str, source_text: str) -> dict:
    """Return {draft, source, oracle, verified}. draft is ItemDraft-shaped and oracle-verified."""
    lang = "sql" if domain == "database" else (language or "python")
    draft = _llm_draft(domain, level, lang, position, source_text)
    source = "ai"
    if draft is None:
        draft = _draft_from_template(_pick_template(domain, level), domain, level, position)
        lang = draft["language"]
        source = "template"
    result = verify_item({"artifact": {"files": [{"path": "solution", "content": draft["code"]}]},
                          "check": draft["check"]})
    return {"draft": draft, "source": source, "verified": result["passed"], "oracle": result["summary"]}
