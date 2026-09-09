from argon2 import PasswordHasher
from argon2.low_level import Type

from src.core.platform.domain.security.auth.credentials.passwords import (
    hash_password,
    password_needs_rehash,
    verify_password,
)


def test_hash_password_creates_an_argon2id_phc_hash() -> None:
    encoded_hash = hash_password("StrongPass123!")

    assert encoded_hash.startswith("$argon2id$v=19$m=19456,t=2,p=1$")
    assert verify_password("StrongPass123!", encoded_hash) is True
    assert password_needs_rehash(encoded_hash) is False


def test_hash_password_uses_a_unique_random_salt() -> None:
    first = hash_password("StrongPass123!")
    second = hash_password("StrongPass123!")

    assert first != second
    assert verify_password("StrongPass123!", first) is True
    assert verify_password("StrongPass123!", second) is True


def test_verify_password_rejects_wrong_password_and_malformed_hash() -> None:
    encoded_hash = hash_password("StrongPass123!")

    assert verify_password("WrongPass123!", encoded_hash) is False
    assert verify_password("StrongPass123!", "$argon2id$invalid") is False
    assert verify_password("StrongPass123!", "") is False


def test_verify_password_rejects_legacy_pbkdf2_and_other_argon2_variants() -> None:
    legacy_pbkdf2 = "pbkdf2_sha256$390000$salt$digest"
    argon2i_hash = PasswordHasher(
        time_cost=2,
        memory_cost=19 * 1024,
        parallelism=1,
        hash_len=32,
        salt_len=16,
        type=Type.I,
    ).hash("StrongPass123!")

    assert verify_password("StrongPass123!", legacy_pbkdf2) is False
    assert verify_password("StrongPass123!", argon2i_hash) is False


def test_weaker_argon2id_profile_is_accepted_but_marked_for_rehash() -> None:
    old_profile_hash = PasswordHasher(
        time_cost=1,
        memory_cost=8 * 1024,
        parallelism=1,
        hash_len=32,
        salt_len=16,
        type=Type.ID,
    ).hash("StrongPass123!")

    assert verify_password("StrongPass123!", old_profile_hash) is True
    assert password_needs_rehash(old_profile_hash) is True

