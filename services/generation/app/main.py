from fastapi import FastAPI

app = FastAPI(title="Generation Service — Core AI #1")

@app.get("/health")
def health():
    return {"service": "generation-service-—-core-ai-#1", "status": "ok"}
