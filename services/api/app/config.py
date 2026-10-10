"""Settings. Defaults to a local SQLite file so it boots with zero setup.
Point DATABASE_URL at Postgres later (one env var) to scale — SQLAlchemy handles the rest."""
import os
try:
    from dotenv import load_dotenv
    load_dotenv()  # loads services/api/.env (where you put LLM_API_KEY) if present
except Exception:
    pass

# SQLite file lives next to the service; no DB server needed for the demo.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./asaanhire.db")
# Some hosts hand out "postgres://..." which SQLAlchemy 2 rejects; normalise it.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8h for demo

# Where the verified seed bank lives (mounted read-only in docker; relative path in dev).
# Resolved from this file's location so it works from any working directory (local, Render, Docker).
_DEFAULT_BANK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "seed_bank.json")
SEED_BANK_PATH = os.getenv("SEED_BANK_PATH", os.path.normpath(_DEFAULT_BANK))

# ---- Deployment ----
# Comma-separated list of allowed browser origins, e.g. "https://asaanhire.vercel.app".
# localhost on any port is always allowed (local dev).
CORS_ORIGINS = [o.strip().rstrip("/") for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
# Seed the item bank, companies and demo candidates on every boot (idempotent).
# Free hosts start with an empty disk, so this keeps the deployed app fully populated.
AUTO_SEED = os.getenv("AUTO_SEED", "1").lower() not in ("0", "false", "no", "")

# ---- LLM grader (OpenAI-compatible; Groq by default) ----
# Set LLM_API_KEY in .env (gitignored). If empty, the grader uses the offline fallback.
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("GROQ_API_KEY", ""))
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
