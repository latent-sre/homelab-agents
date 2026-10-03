"""Kernel digests: bytes in, one convention out, and framing that cannot collide."""

from __future__ import annotations

import unittest

from fleet import digest


class DigestTests(unittest.TestCase):
    def test_framed_digest_separates_name_and_body_boundaries(self) -> None:
        one = digest.framed_sha256([("a", b"bc")], domain=b"d")
        two = digest.framed_sha256([("ab", b"c")], domain=b"d")
        self.assertNotEqual(one, two)
        self.assertNotEqual(one, digest.framed_sha256([("a", b"bc")], domain=b"other"))
        self.assertEqual(one, digest.framed_sha256(iter([("a", b"bc")]), domain=b"d"))


if __name__ == "__main__":
    unittest.main()
