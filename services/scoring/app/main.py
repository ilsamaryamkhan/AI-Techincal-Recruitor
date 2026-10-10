from fastapi import FastAPI

app = FastAPI(title="Scoring Service — Core AI #2 brain")

@app.get("/health")
def health():
    return {"service": "scoring-service-—-core-ai-#2-brain", "status": "ok"}
