class DedupStore:
    """Redis-shaped interface so tests can inject a dict backend."""

    def __init__(self, redis_client):
        self.r = redis_client

    def claim(self, payment_id: str, event_type: str, ttl_seconds: int = 86400) -> bool:
        key = f"evt:{payment_id}:{event_type}"
        return bool(self.r.set(key, "1", nx=True, ex=ttl_seconds))
