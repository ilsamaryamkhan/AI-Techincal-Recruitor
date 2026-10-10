"""asaanHire API gateway."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import engine, Base
from .routers import auth, items, companies, practice, recruiter, interview, company


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist. (Swap for Alembic migrations when the schema stabilizes.)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="asaanHire API", lifespan=lifespan)

# Dev CORS: accept the Next.js frontend on ANY local port. Next picks 3001, 3002…
# whenever 3000 is already taken, so pinning one port causes "Failed to fetch".
# The regex covers localhost / 127.0.0.1 on any port; tighten this for production.
app.add_middleware(
    CORSMiddleware,
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
