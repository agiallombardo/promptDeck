from functools import lru_cache

from app.config import get_settings
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


@lru_cache
def _password_hasher(time_cost: int, memory_cost: int, parallelism: int) -> PasswordHasher:
    return PasswordHasher(
        time_cost=time_cost,
        memory_cost=memory_cost,
        parallelism=parallelism,
    )


def _active_hasher() -> PasswordHasher:
    s = get_settings()
    return _password_hasher(s.argon2_time_cost, s.argon2_memory_cost, s.argon2_parallelism)


def hash_password(plain: str) -> str:
    return _active_hasher().hash(plain)


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return _active_hasher().verify(password_hash, plain)
    except VerifyMismatchError:
        return False
