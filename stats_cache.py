"""In-memory TTL cache for expensive database aggregations."""

import time
from threading import Lock


class StatsCache:
    def __init__(self):
        self._store = {}
        self._lock = Lock()

    def get(self, key):
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.time() > entry["expires_at"]:
                del self._store[key]
                return None
            return entry["value"]

    def set(self, key, value, ttl=300):
        with self._lock:
            self._store[key] = {
                "value": value,
                "expires_at": time.time() + ttl,
            }

    def invalidate(self, pattern=None):
        with self._lock:
            if pattern is None:
                self._store.clear()
                return
            keys_to_delete = [k for k in self._store if pattern in k]
            for k in keys_to_delete:
                del self._store[k]

    def stats(self):
        with self._lock:
            now = time.time()
            total = len(self._store)
            expired = sum(1 for e in self._store.values() if now > e["expires_at"])
            return {"total_entries": total, "expired": expired, "active": total - expired}
