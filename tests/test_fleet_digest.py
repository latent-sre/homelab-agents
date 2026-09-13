"""Kernel digests: bytes in, one convention out, and framing that cannot collide."""

from __future__ import annotations

import hashlib
import unittest

from fleet import digest
from tests.support import TempDirTestCase


class DigestTests(TempDirTestCase):
    def test_hex_digest_matches_hashlib_and_file_digest_reads_raw_bytes(self) -> None:
        self.assertEqual(digest.sha256_hex(b"abc"), hashlib.sha256(b"abc").hexdigest())
        path = self.base / "crlf.txt"
        path.write_bytes(b"a\r\nb")
        # No newline translation: the digest names the bytes on disk, not a decoded view.
        self.assertEqual(digest.sha256_file(path), hashlib.sha256(b"a\r\nb").hexdigest())

    def test_framed_digest_separates_name_and_body_boundaries(self) -> None:
        one = digest.framed_sha256([("a", b"bc")], domain=b"d")
        two = digest.framed_sha256([("ab", b"c")], domain=b"d")
        self.assertNotEqual(one, two)
        self.assertNotEqual(one, digest.framed_sha256([("a", b"bc")], domain=b"other"))
        self.assertEqual(one, digest.framed_sha256(iter([("a", b"bc")]), domain=b"d"))


if __name__ == "__main__":
    unittest.main()
