"""PII normalization and hashing for Reddit Advanced Matching.

Reddit expects personally identifiable match keys (email, phone) to be
normalized and SHA-256 hashed before they leave your servers. Identifiers used
purely for attribution/dedup (click id, Reddit uuid, conversion id) are sent in
the clear — hashing them would break matching.
"""
from __future__ import annotations

import hashlib
import re


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_email(email: str) -> str:
    """Trim and lowercase. (Gmail dot/plus normalization intentionally left out —
    Reddit does not require it and it can reduce match rates if applied wrongly.)"""
    return email.strip().lower()


def normalize_phone(phone: str) -> str:
    """Strip everything except digits. Callers should include country code."""
    return re.sub(r"\D", "", phone)


def hash_email(email: str) -> str:
    return sha256_hex(normalize_email(email))


def hash_phone(phone: str) -> str:
    return sha256_hex(normalize_phone(phone))


def is_sha256_hex(value: str) -> bool:
    """True if the value already looks hashed, so we never double-hash."""
    return bool(re.fullmatch(r"[a-f0-9]{64}", value or ""))


def maybe_hash_email(email: str) -> str:
    return email if is_sha256_hex(email) else hash_email(email)


def maybe_hash_phone(phone: str) -> str:
    return phone if is_sha256_hex(phone) else hash_phone(phone)


def hash_generic(value: str) -> str:
    """For external_id / IDFA / AAID: normalize (trim + lowercase) then SHA-256.
    Reddit Advanced Matching hashes these alongside email and phone."""
    return sha256_hex(value.strip().lower())


def maybe_hash_generic(value: str) -> str:
    return value if is_sha256_hex(value) else hash_generic(value)
