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

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8h for demo

# Where the verified seed bank lives (mounted read-only in docker; relative path in dev).
SEED_BANK_PATH = os.getenv("SEED_BANK_PATH", "../../data/seed_bank.json")

# ---- LLM grader (OpenAI-compatible; Groq by default) ----
# Set LLM_API_KEY in .env (gitignored). If empty, the grader uses the offline fallback.
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("GROQ_API_KEY", ""))
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
