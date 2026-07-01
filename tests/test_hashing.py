from capi_connector.hashing import (
    hash_email,
    is_sha256_hex,
    maybe_hash_email,
    normalize_email,
    normalize_phone,
    sha256_hex,
)


def test_normalize_email_trims_and_lowercases():
    assert normalize_email("  Ashley.Chen@Example.COM ") == "ashley.chen@example.com"


def test_normalize_phone_keeps_digits_only():
    assert normalize_phone("+1 (415) 555-0132") == "14155550132"


def test_hash_email_is_deterministic_and_sha256():
    a = hash_email("test@example.com")
    b = hash_email("TEST@example.com  ")  # normalization makes these equal
    assert a == b
    assert is_sha256_hex(a)


def test_sha256_known_value():
    # sanity check against a known digest
    assert sha256_hex("") == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


def test_maybe_hash_email_does_not_double_hash():
    already = hash_email("test@example.com")
    assert maybe_hash_email(already) == already
