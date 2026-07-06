import hashlib


def create_sha256() -> "hashlib._Hash":
    return hashlib.sha256()

