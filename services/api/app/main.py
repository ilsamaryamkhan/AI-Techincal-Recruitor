"""asaanHire API gateway."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import engine, Base
from .routers import auth, items


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist. (Swap for Alembic migrations when the schema stabilizes.)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="asaanHire API", lifespan=lifespan)

# Dev CORS: let the Next.js frontend (localhost:3000) call us.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(items.router)


@app.get("/health")
def health():
    return {"service": "asaanhire-api", "status": "ok"}
