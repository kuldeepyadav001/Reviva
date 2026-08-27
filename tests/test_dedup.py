from reviva_shared.dedup import DedupStore


class MemoryRedis:
    def __init__(self):
        self._d = {}

    def set(self, key, val, nx=False, ex=None):
        if nx and key in self._d:
            return False
        self._d[key] = val
        return True


def test_claim_once():
    d = DedupStore(MemoryRedis())
    assert d.claim("pay_1", "payment.failed") is True
    assert d.claim("pay_1", "payment.failed") is False
    assert d.claim("pay_1", "payment.captured") is True
