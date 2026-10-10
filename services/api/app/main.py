"""asaanHire API gateway."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import engine, Base
from .config import CORS_ORIGINS, AUTO_SEED
from .routers import auth, items, companies, practice, recruiter, interview, company


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist. (Swap for Alembic migrations when the schema stabilizes.)
    Base.metadata.create_all(bind=engine)
    if AUTO_SEED:
        # Idempotent: fills an empty database (fresh deploy), no-ops on a populated one.
        try:
            from .seed_loader import load_seed_bank
            from .seed_candidates import seed_candidates
            load_seed_bank()
            seed_candidates()
        except Exception as e:  # never block the API from booting
            print(f"[startup] auto-seed skipped: {e}")
    yield


app = FastAPI(title="asaanHire API", lifespan=lifespan)

# CORS: localhost / 127.0.0.1 on any port (Next picks 3001, 3002… when 3000 is taken),
# plus any deployed frontend listed in the CORS_ORIGINS env var (comma-separated).
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(items.router)
app.include_router(companies.router)
app.include_router(practice.router)
app.include_router(recruiter.router)
app.include_router(interview.router)
app.include_router(company.router)


@app.get("/health")
def health():
    return {"service": "asaanhire-api", "status": "ok"}
