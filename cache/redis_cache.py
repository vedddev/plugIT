import hashlib
import json
import redis


class RedisCache:
    def __init__(self, host="localhost", port=6379, db=0, ttl=3600):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.ttl = ttl

    def _key(self, prompt: str, model: str, system_prompt: str | None = None, generation: dict | None = None):
        raw = json.dumps({"model": model, "prompt": prompt, "system_prompt": system_prompt or "", "generation": generation or {}}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, prompt: str, model: str, system_prompt: str | None = None, generation: dict | None = None):
        value = self.client.get(self._key(prompt, model, system_prompt, generation))
        return json.loads(value) if value else None

    def set(self, prompt: str, model: str, response: dict, system_prompt: str | None = None, generation: dict | None = None):
        self.client.setex(self._key(prompt, model, system_prompt, generation), self.ttl, json.dumps(response))
