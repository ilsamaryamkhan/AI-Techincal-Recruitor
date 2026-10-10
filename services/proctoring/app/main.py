from fastapi import FastAPI

app = FastAPI(title="Proctoring Service — Core AI #3")

@app.get("/health")
def health():
    return {"service": "proctoring-service-—-core-ai-#3", "status": "ok"}
