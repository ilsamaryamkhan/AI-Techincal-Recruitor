# Contracts — the source of truth

Four people build against these. **Do not change a field without telling the team**;
every service serializes to/from these shapes.

- `generated_item.schema.json` — Core AI #1 output; what practice + interview consume.
  `fault_label` and `verification` are **SERVER-ONLY** — strip them before any item
  reaches a candidate's browser, or the answer leaks in the network tab.
- `interview_session.schema.json` — the runtime <-> proctoring <-> scoring contract.
- `fault_taxonomy.json` — the ground-truth fault catalogue. Every generated item
  carries exactly one `fault_id` from here (or is a verified decoy).

Validate anything against a schema:
```bash
pip install jsonschema
python -c "import json,jsonschema; jsonschema.validate(json.load(open('data/seed_bank.json'))['items'][0], json.load(open('contracts/generated_item.schema.json')))"
```
