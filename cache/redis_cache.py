import hashlib
import json

import redis


class RedisCache:

    def __init__(
        self,
        host="localhost",
        port=6379,
        db=0,
        ttl=3600,
    ):
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
        )

        self.ttl = ttl

    def _key(self, prompt: str, model: str):

        raw = f"{model}:{prompt}"

        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, prompt: str, model: str):

        key = self._key(prompt, model)

        value = self.client.get(key)

        if value:

            return json.loads(value)

        return None

    def set(
        self,
        prompt: str,
        model: str,
        response: dict,
    ):

        key = self._key(prompt, model)

        self.client.setex(
            key,
            self.ttl,
            json.dumps(response),
        )