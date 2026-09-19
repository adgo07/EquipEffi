from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.validate_portable_bundle import REQUIRED_MEMBERS, validate


class PortableBundleValidatorTests(unittest.TestCase):
    def _make_bundle(self, path: Path, *, corrupt: bool = False) -> None:
        files = {name: b"x" for name in REQUIRED_MEMBERS if name != "SHA256SUMS.txt"}
        files["equipeffi-0.2.1-py3-none-any.whl"] = b"wheel"
        files["equipeffi.pyz"] = b"pyz"
        checksums = "# test\n" + "\n".join(
            f"{hashlib.sha256(content).hexdigest()}  {name}" for name, content in sorted(files.items())
        ) + "\n"
        files["SHA256SUMS.txt"] = checksums.encode("utf-8")
        with zipfile.ZipFile(path, "w") as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        if corrupt:
            # append a duplicate member with changed content; validator must reject it
            with zipfile.ZipFile(path, "a") as archive:
                archive.writestr("equipeffi.pyz", b"changed")

    def test_valid_bundle_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "portable.zip"
            self._make_bundle(path)
            result = validate(path)
            self.assertTrue(result["is_valid"], result["errors"])
            self.assertEqual(result["checks"]["checksum_errors"], [])

    def test_duplicate_or_hash_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "portable.zip"
            self._make_bundle(path, corrupt=True)
            result = validate(path)
            self.assertFalse(result["is_valid"])
            self.assertTrue(result["checks"]["duplicate_members"])


if __name__ == "__main__":
    unittest.main()
