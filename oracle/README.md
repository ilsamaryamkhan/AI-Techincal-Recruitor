# Oracle — the verification harness

Core AI #1 proposes items; the oracle **proves** each injected fault actually changes
behaviour before the item is admitted. No fault that bites -> item is `rejected`.

`verify_seed_bank.py` runs the real checks on the seed bank:
- `perf_test`  — timing curve confirms the claimed complexity (D1-1: ~370x).
- `hidden_test`— injected fault produces wrong output (D1-2, D1-3).
- `query_diff` — faulty SQL returns a different result set than the correct one (D3-1, D3-2).

```bash
python oracle/verify_seed_bank.py   # expect five VERIFIED lines
```

Phase 1: generalize each check into a method the generation service calls per item.
Mapping: method name here == `verified_by` in `contracts/fault_taxonomy.json`.
