"""Settings. Defaults to a local SQLite file so it boots with zero setup.
Point DATABASE_URL at Postgres later (one env var) to scale — SQLAlchemy handles the rest."""
import os

# SQLite file lives next to the service; no DB server needed for the demo.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./asaanhire.db")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8h for demo

# Where the verified seed bank lives (mounted read-only in docker; relative path in dev).
SEED_BANK_PATH = os.getenv("SEED_BANK_PATH", "../../data/seed_bank.json")
