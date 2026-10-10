from fastapi import FastAPI

app = FastAPI(title="Interview Service — session orchestrator")

@app.get("/health")
def health():
    return {"service": "interview-service-—-session-orchestrator", "status": "ok"}
