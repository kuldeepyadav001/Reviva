from fastapi import FastAPI
from reviva_shared.health import service_health

app = FastAPI(title="reviva-executor")


@app.get("/health")
def health():
    return service_health("executor-service")
