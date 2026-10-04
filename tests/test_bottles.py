"""Tests for bottle metadata validation with small synthetic archives."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check-bottles.py"
SPEC = importlib.util.spec_from_file_location("check_bottles", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
check_bottles = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_bottles)


VERSION = "2.4.1"
TARGETS = ("arm64_sequoia", "x86_64_linux")
RELEASE_ROOT = f"https://github.com/btfranklin/homebrew-tap/releases/download/perfect-doc-{VERSION}"


class BottleValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.archive_bytes = {
            "arm64_sequoia": b"synthetic macOS bottle bytes\n",
            "x86_64_linux": b"synthetic Linux bottle bytes\n",
        }
        self.metadata_paths: dict[str, Path] = {}
        for target in TARGETS:
            self._write_target(target)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _write_target(self, target: str, *, archive_bytes: bytes | None = None) -> Path:
        public_name = f"perfect-doc-{VERSION}.{target}.bottle.tar.gz"
        local_name = f"perfect-doc--{VERSION}.{target}.bottle.tar.gz"
        content = archive_bytes if archive_bytes is not None else self.archive_bytes[target]
        (self.directory / local_name).write_bytes(content)
        value = {
            "btfranklin/tap/perfect-doc": {
                "formula": {
                    "name": "perfect-doc",
                    "pkg_version": VERSION,
                    "path": "Library/Taps/btfranklin/homebrew-tap/Formula/perfect-doc.rb",
                    "tap_git_path": "Formula/perfect-doc.rb",
                    "license": "MIT",
                },
                "bottle": {
                    "root_url": RELEASE_ROOT,
                    "rebuild": 0,
                    "tags": {
                        target: {
                            "filename": public_name,
                            "local_filename": local_name,
                            "sha256": hashlib.sha256(content).hexdigest(),
                        }
                    },
                },
            }
        }
        metadata_path = self.directory / f"perfect-doc--{VERSION}.{target}.bottle.json"
        metadata_path.write_text(json.dumps(value), encoding="utf-8")
        self.metadata_paths[target] = metadata_path
        return metadata_path

    def _metadata(self, target: str) -> dict[str, object]:
        path = self.metadata_paths[target]
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_metadata(self, target: str, value: dict[str, object]) -> None:
        self.metadata_paths[target].write_text(json.dumps(value), encoding="utf-8")

    def test_accepts_both_targets_and_matching_archives(self) -> None:
        check_bottles.validate_bottles(self.directory, VERSION)

    def test_homebrew_rebuild(self) -> None:
        for path in self.metadata_paths.values():
            metadata = json.loads(path.read_text())
            bottle = metadata[check_bottles.FORMULA]["bottle"]
            bottle["rebuild"] = 1
            for tag in bottle["tags"].values():
                old_name = tag["local_filename"]
                tag["filename"] = tag["filename"].replace(".bottle.tar.gz", ".bottle.1.tar.gz")
                tag["local_filename"] = old_name.replace(".bottle.tar.gz", ".bottle.1.tar.gz")
                (self.directory / old_name).rename(self.directory / tag["local_filename"])
            path.write_text(json.dumps(metadata))
        check_bottles.validate_bottles(self.directory, VERSION)

    def test_rejects_a_missing_target(self) -> None:
        self.metadata_paths["x86_64_linux"].unlink()
        (self.directory / "perfect-doc--2.4.1.x86_64_linux.bottle.tar.gz").unlink()

        with self.assertRaisesRegex(check_bottles.BottleError, "exactly two .bottle.json"):
            check_bottles.validate_bottles(self.directory, VERSION)

    def test_rejects_a_missing_archive(self) -> None:
        (self.directory / "perfect-doc--2.4.1.x86_64_linux.bottle.tar.gz").unlink()

        with self.assertRaisesRegex(check_bottles.BottleError, "expected exactly two"):
            check_bottles.validate_bottles(self.directory, VERSION)

    def test_rejects_wrong_formula_version(self) -> None:
        value = self._metadata("arm64_sequoia")
        package = value["btfranklin/tap/perfect-doc"]
        package["formula"]["pkg_version"] = "2.4.0"
        self._save_metadata("arm64_sequoia", value)

        with self.assertRaisesRegex(check_bottles.BottleError, "pkg_version"):
            check_bottles.validate_bottles(self.directory, VERSION)

    def test_rejects_wrong_release_root(self) -> None:
        value = self._metadata("arm64_sequoia")
        package = value["btfranklin/tap/perfect-doc"]
        package["bottle"]["root_url"] = "https://example.com/release"
        self._save_metadata("arm64_sequoia", value)

        with self.assertRaisesRegex(check_bottles.BottleError, "root_url"):
            check_bottles.validate_bottles(self.directory, VERSION)

    def test_rejects_archive_checksum_mismatch(self) -> None:
        archive = self.directory / "perfect-doc--2.4.1.arm64_sequoia.bottle.tar.gz"
        archive.write_bytes(b"changed archive bytes\n")

        with self.assertRaisesRegex(check_bottles.BottleError, "SHA-256 mismatch"):
            check_bottles.validate_bottles(self.directory, VERSION)

    def test_rejects_duplicate_target(self) -> None:
        value = self._metadata("x86_64_linux")
        package = value["btfranklin/tap/perfect-doc"]
        package["bottle"]["tags"] = self._metadata("arm64_sequoia")["btfranklin/tap/perfect-doc"]["bottle"]["tags"]
        self._save_metadata("x86_64_linux", value)

        with self.assertRaisesRegex(check_bottles.BottleError, "duplicate bottle target"):
            check_bottles.validate_bottles(self.directory, VERSION)


if __name__ == "__main__":
    unittest.main()
