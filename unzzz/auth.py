"""Password hashing, cookie sessions and login throttling."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from .db import Store

PBKDF2_ITERATIONS = 210_000
SESSION_COOKIE = "unzzz_session"
SESSION_TTL = 30 * 24 * 3600  # 30 days
MIN_PASSWORD_LEN = 8
MAX_PASSWORD_LEN = 256


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algo, iterations, salt, digest = encoded.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        got = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), int(iterations)
        ).hex()
        return hmac.compare_digest(got, digest)
    except (ValueError, TypeError):
        return False


def session_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class LoginThrottle:
    """Small in-memory failure counter, keyed by client IP."""

    WINDOW = 5 * 60
    MAX_FAILURES = 5
    LOCKOUT = 5 * 60

    def __init__(self) -> None:
        self._failures: dict[str, list[float]] = {}
        self._locked: dict[str, float] = {}

    def retry_after(self, ip: str, now: float | None = None) -> int:
        now = time.time() if now is None else now
        until = self._locked.get(ip)
        if until and until > now:
            return max(1, int(until - now) + 1)
        return 0

    def fail(self, ip: str, now: float | None = None) -> int:
        now = time.time() if now is None else now
        hits = [t for t in self._failures.get(ip, []) if now - t < self.WINDOW]
        hits.append(now)
        self._failures[ip] = hits
        if len(hits) >= self.MAX_FAILURES:
            self._locked[ip] = now + self.LOCKOUT
            self._failures.pop(ip, None)
            return self.LOCKOUT
        return 0

    def reset(self, ip: str) -> None:
        self._failures.pop(ip, None)
        self._locked.pop(ip, None)


class Auth:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.throttle = LoginThrottle()

    # ------------------------------------------------------------- password
    @property
    def configured(self) -> bool:
        return bool(self.store.get_setting("admin_password"))

    def set_password(self, password: str, *, keep_hash: str | None = None) -> None:
        self.store.set_setting("admin_password", hash_password(password))
        self.store.delete_other_sessions(keep_hash)

    def check_password(self, password: str) -> bool:
        return verify_password(password, self.store.get_setting("admin_password"))

    # -------------------------------------------------------------- sessions
    def new_session(self, user_agent: str = "") -> str:
        token = secrets.token_urlsafe(32)
        self.store.add_session(
            session_hash(token), time.time() + SESSION_TTL, user_agent
        )
        return token

    def session_valid(self, token: str | None) -> bool:
        if not token:
            return False
        return self.store.get_session(session_hash(token)) is not None

    def destroy_session(self, token: str | None) -> None:
        if token:
            self.store.delete_session(session_hash(token))

    # -------------------------------------------------------------- throttle
    def locked_for(self, ip: str) -> int:
        return self.throttle.retry_after(ip)

    def note_failure(self, ip: str) -> int:
        return self.throttle.fail(ip)

    def note_success(self, ip: str) -> None:
        self.throttle.reset(ip)
