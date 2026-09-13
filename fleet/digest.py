"""Content identity: one SHA-256 convention for every instrument that names bytes.

A digest is a claim about exactly which bytes were measured or shipped, and two instruments
that hash the same tree by different conventions produce two identities nothing can arbitrate.
Hash bytes, never text: a text digest silently depends on the decoder and the platform newline.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """The digest of a file's bytes as they are on disk (no newline or encoding translation)."""
    return sha256_hex(Path(path).read_bytes())


def framed_sha256(parts: Iterable[tuple[str, bytes]], *, domain: bytes) -> str:
    """A length-framed digest over named parts, so no concatenation of parts can collide.

    Plain concatenation lets `("a", b"bc")` and `("ab", b"c")` hash alike; framing each name
    and each body by its length before the bytes removes that ambiguity, and the `domain`
    prefix keeps two framings of different things from ever comparing equal by accident.
    """
    digest = hashlib.sha256(domain)
    for name, body in parts:
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(len(body).to_bytes(8, "big"))
        digest.update(body)
    return digest.hexdigest()
