"""Grounding — turn the item's code into ground-truth FACTS.

This is what makes the grader more than an LLM wrapper: claims in a candidate's
explanation are checked against facts we derive from the code itself (via Python's
AST for Python items, light token analysis for SQL). A candidate who says
"it's O(n) with a hash set" about code where `seen` is a list gets caught here.

Output shape (stable, consumed by grader + LLM prompt):
  {
    "language": "python",
    "facts": ["`seen` is a list, so `in seen` is O(n)", ...],   # human-readable
    "flags": {            # structured, for deterministic checks
      "list_membership_in_loop": True,
      "has_nested_loops": False,
      "mutable_default_args": ["cart"],
      "loop_bound_strict_lt": True,
      ...
    }
  }
"""
from __future__ import annotations
import ast
import re


def ground(language: str, code: str) -> dict:
    if language == "python":
        return _ground_python(code)
    if language == "sql":
        return _ground_sql(code)
    return {"language": language, "facts": [], "flags": {}}


# --------------------------------------------------------------------------- python
def _ground_python(code: str) -> dict:
    facts: list[str] = []
    flags: dict = {}
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"language": "python", "facts": ["(code did not parse)"], "flags": {}}

    # names assigned a list literal / list() vs set()/dict()
    list_vars, set_vars = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            tgt = node.targets[0]
            name = tgt.id if isinstance(tgt, ast.Name) else None
            v = node.value
            if name:
                if isinstance(v, ast.List) or (isinstance(v, ast.Call) and _callee(v) == "list"):
                    list_vars.add(name)
                elif isinstance(v, ast.Set) or (isinstance(v, ast.Call) and _callee(v) == "set"):
                    set_vars.add(name)
    if list_vars: facts.append(f"list variable(s): {', '.join(sorted(list_vars))}")
    if set_vars:  facts.append(f"set variable(s): {', '.join(sorted(set_vars))}")

    # membership test `x in Y` where Y is a list var, and whether it sits inside a loop
    list_membership_in_loop = False
    for loop in [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]:
        for sub in ast.walk(loop):
            if isinstance(sub, ast.Compare) and any(isinstance(op, ast.In) for op in sub.ops):
                comp = sub.comparators[0]
                if isinstance(comp, ast.Name) and comp.id in list_vars:
                    list_membership_in_loop = True
                    facts.append(f"`in {comp.id}` runs inside a loop and `{comp.id}` is a list → O(n) membership → O(n^2) overall")
    flags["list_membership_in_loop"] = list_membership_in_loop

    # nested loops
    max_depth = _max_loop_depth(tree)
    flags["max_loop_depth"] = max_depth
    if max_depth >= 2:
        facts.append(f"nested loops detected (depth {max_depth})")

    # mutable default args
    mut = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for arg, default in _args_with_defaults(fn):
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                mut.append(arg)
                facts.append(f"function `{fn.name}` has a mutable default argument `{arg}` (shared across calls)")
    flags["mutable_default_args"] = mut

    # while-loop bound: strict < vs <= (off-by-one smell)
    strict_lt = False
    for w in [n for n in ast.walk(tree) if isinstance(n, ast.While)]:
        if isinstance(w.test, ast.Compare) and any(isinstance(op, ast.Lt) for op in w.test.ops):
            strict_lt = True
            facts.append("while-loop uses a strict `<` bound (check it doesn't skip the final element)")
    flags["loop_bound_strict_lt"] = strict_lt

    # recursion (self-call)
    rec = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if any(isinstance(c, ast.Call) and _callee(c) == fn.name for c in ast.walk(fn)):
            rec.append(fn.name)
    flags["recursive_functions"] = rec
    if rec: facts.append(f"recursive function(s): {', '.join(rec)}")

    return {"language": "python", "facts": facts, "flags": flags}


def _callee(call: ast.Call):
    if isinstance(call.func, ast.Name): return call.func.id
    if isinstance(call.func, ast.Attribute): return call.func.attr
    return None

def _args_with_defaults(fn: ast.FunctionDef):
    args = fn.args.args
    defaults = fn.args.defaults
    paired = list(zip(args[len(args) - len(defaults):], defaults)) if defaults else []
    return [(a.arg, d) for a, d in paired]

def _max_loop_depth(tree) -> int:
    def depth(node, d=0):
        best = d
        for child in ast.iter_child_nodes(node):
            nd = d + 1 if isinstance(child, (ast.For, ast.While)) else d
            best = max(best, depth(child, nd))
        return best
    return depth(tree)


# --------------------------------------------------------------------------- sql
def _ground_sql(code: str) -> dict:
    facts, flags = [], {}
    c = code.lower()
    flags["has_join"] = " join " in c
    flags["has_left_join"] = "left join" in c
    flags["has_group_by"] = "group by" in c
    flags["count_star"] = bool(re.search(r"count\s*\(\s*\*\s*\)", c))
    flags["has_sum"] = "sum(" in c
    if flags["has_join"] and flags["has_sum"]:
        facts.append("aggregates (SUM) over a JOIN — if the join is one-to-many, rows fan out and the sum inflates")
    if flags["has_left_join"] and flags["count_star"]:
        facts.append("COUNT(*) over a LEFT JOIN counts the NULL-padded row for a non-matching parent as 1, not 0")
    if flags["has_join"]:
        facts.append("query joins multiple tables — check the join cardinality (one-to-one vs one-to-many)")
    return {"language": "sql", "facts": facts, "flags": flags}
