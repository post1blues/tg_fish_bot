import redis

from config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD

_database = None


def get_database_connection():
    global _database
    if _database is None:
        _database = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)
    return _database






