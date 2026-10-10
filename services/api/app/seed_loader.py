"""Load data/seed_bank.json into the DB. Idempotent: re-running updates in place.

Run it:   (from services/api, venv active)
    python -m app.seed_loader
"""
import json
import os
from .db import SessionLocal, engine, Base
from .models import Company, Item
from .config import SEED_BANK_PATH

# Display names for the demo companies (slug -> label).
COMPANY_NAMES = {
    "devsinc": "Devsinc", "systems": "Systems Limited", "techlogix": "Techlogix",
    "10pearls": "10Pearls", "arbisoft": "Arbisoft", "netsol": "NETSOL Technologies",
    "folio3": "Folio3", "confiz": "Confiz", "venturedive": "VentureDive", "i2c": "i2c Inc.",
}


def load_seed_bank(path: str | None = None) -> dict:
    path = path or SEED_BANK_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"seed bank not found at {path} (set SEED_BANK_PATH)")
    with open(path, encoding="utf-8") as f:
        bank = json.load(f)
    items = bank["items"]

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    n_items = 0
    try:
        # one set tracks every company id already present or queued, so we never
        # add a duplicate (pending adds aren't visible to db.get until flush).
        existing = {c.id for c in db.query(Company).all()}
        # seed all 10 demo companies up front (signup dropdown + pool stay full,
        # even though only some currently have items)
        for cid, cname in COMPANY_NAMES.items():
            if cid not in existing:
                db.add(Company(id=cid, name=cname)); existing.add(cid)
        for it in items:
            cid = it["company_id"]
            if cid not in existing:
                db.add(Company(id=cid, name=COMPANY_NAMES.get(cid, cid.title()))); existing.add(cid)
            row = db.get(Item, it["item_id"])
            if row:                                   # update
                row.company_id, row.domain, row.level = cid, it["domain"], it["level"]
                row.mode, row.language, row.payload = it["mode"], it["language"], it
            else:                                     # insert
                db.add(Item(
                    id=it["item_id"], company_id=cid, domain=it["domain"],
                    level=it["level"], mode=it["mode"], language=it["language"], payload=it,
                ))
            n_items += 1
        db.commit()
        total_companies = db.query(Company).count()
    finally:
        db.close()
    summary = {"companies": total_companies, "items": n_items}
    print(f"seeded {summary['items']} items across {summary['companies']} companies from {path}")
    return summary


if __name__ == "__main__":
    load_seed_bank()
