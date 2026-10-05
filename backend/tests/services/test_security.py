from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password


def test_hash_is_not_plaintext_and_verifies():
    hashed = hash_password("abc123")

    assert hashed != "abc123"
    assert verify_password("abc123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_same_password_gives_different_hashes():
    # bcrypt adds a random salt each time
    assert hash_password("abc123") != hash_password("abc123")


def test_token_contains_subject_and_future_expiry():
    token = create_access_token("42")

    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

    assert payload["sub"] == "42"
    assert payload["exp"] > datetime.now(timezone.utc).timestamp()


def test_token_signed_with_other_key_is_rejected():
    forged = jwt.encode({"sub": "1"}, "some-other-secret-that-is-long-enough-32b", algorithm=settings.algorithm)

    with pytest.raises(jwt.InvalidTokenError):
        jwt.decode(forged, settings.secret_key, algorithms=[settings.algorithm])


def test_expired_token_is_rejected():
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.secret_key,
        algorithm=settings.algorithm,
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(expired, settings.secret_key, algorithms=[settings.algorithm])
