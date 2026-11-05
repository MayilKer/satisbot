import hashlib
import json

import redis

from app.config import settings

r = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def normalize(text: str) -> str:
    """«  Qadın üçün  ŞİRİN ətir » и «qadın üçün şirin ətir» → один ключ кэша."""
    return " ".join(text.split()).lower()


def make_key(prefix: str, *parts) -> str:
    raw = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    return f"{prefix}:{hashlib.sha1(raw.encode()).hexdigest()}"


def get_json(key: str):
    value = r.get(key)
    return json.loads(value) if value is not None else None


def set_json(key: str, value, ttl: int) -> None:
    r.set(key, json.dumps(value), ex=ttl)


def delete_prefix(prefix: str) -> int:
    deleted = 0
    for key in r.scan_iter(match=f"{prefix}*", count=500):  # SCAN, а не KEYS: не блокирует Redis
        deleted += r.delete(key)
    return deleted