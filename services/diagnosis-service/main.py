from fastapi import FastAPI
from reviva_shared.health import service_health

app = FastAPI(title="reviva-diagnosis")


@app.get("/health")
def health():
    return service_health("diagnosis-service")
