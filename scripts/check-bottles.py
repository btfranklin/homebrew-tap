#!/usr/bin/env python3
"""Check Homebrew bottle metadata and archives before publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


FORMULA = "btfranklin/tap/perfect-doc"
FORMULA_NAME = "perfect-doc"
FORMULA_PATH = "Library/Taps/btfranklin/homebrew-tap/Formula/perfect-doc.rb"
TAP_GIT_PATH = "Formula/perfect-doc.rb"
RELEASE_ROOT = "https://github.com/btfranklin/homebrew-tap/releases/download"
TARGETS = ("arm64_sequoia", "x86_64_linux")


class BottleError(Exception):
    """A bottle input does not match the release contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BottleError(message)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BottleError(f"cannot read metadata {path.name}: {error}") from error
    _require(isinstance(value, dict), f"metadata {path.name} must contain a JSON object")
    return value


def _expected_paths(version: str, target: str) -> tuple[str, str]:
    public_name = f"perfect-doc-{version}.{target}.bottle.tar.gz"
    local_name = f"perfect-doc--{version}.{target}.bottle.tar.gz"
    return public_name, local_name


def validate_bottles(directory: Path, version: str) -> None:
    """Validate the two supported bottle metadata files and archives."""
    _require(bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", version)), "version must be a simple release version")
    _require(directory.is_dir(), f"bottle directory does not exist: {directory}")

    entries = list(directory.iterdir())
    metadata_files = sorted(path for path in entries if path.name.endswith(".bottle.json"))
    archives = sorted(path for path in entries if path.name.endswith(".tar.gz"))
    _require(len(metadata_files) == 2, f"expected exactly two .bottle.json files; found {len(metadata_files)}")
    _require(len(archives) == 2, f"expected exactly two .bottle.tar.gz archives and no stray archives; found {len(archives)} .tar.gz files")
    _require(all(path.name.endswith(".bottle.tar.gz") for path in archives), "found a stray archive; every .tar.gz file must be a bottle archive")

    found_targets: set[str] = set()
    found_archives: set[str] = set()
    expected_root = f"{RELEASE_ROOT}/perfect-doc-{version}"
    for metadata_path in metadata_files:
        metadata = _read_json(metadata_path)
        _require(set(metadata) == {FORMULA}, f"metadata {metadata_path.name} must contain only {FORMULA}")
        package = metadata[FORMULA]
        _require(isinstance(package, dict), f"metadata {metadata_path.name} has an invalid formula record")
        formula = package.get("formula")
        bottle = package.get("bottle")
        _require(isinstance(formula, dict), f"metadata {metadata_path.name} is missing formula details")
        _require(isinstance(bottle, dict), f"metadata {metadata_path.name} is missing bottle details")

        expected_fields = {
            "name": FORMULA_NAME,
            "pkg_version": version,
            "path": FORMULA_PATH,
            "tap_git_path": TAP_GIT_PATH,
            "license": "MIT",
        }
        for key, expected in expected_fields.items():
            _require(formula.get(key) == expected, f"{metadata_path.name}: formula {key} must be {expected!r}")

        _require(bottle.get("root_url") == expected_root, f"{metadata_path.name}: bottle root_url must be {expected_root!r}")
        rebuild = bottle.get("rebuild")
        _require(type(rebuild) is int and rebuild == 0, f"{metadata_path.name}: bottle rebuild must be 0")
        tags = bottle.get("tags")
        _require(isinstance(tags, dict), f"{metadata_path.name}: bottle tags must be an object")
        _require(len(tags) == 1, f"{metadata_path.name}: expected exactly one target tag")

        for target, tag in tags.items():
            _require(target in TARGETS, f"{metadata_path.name}: unsupported bottle target {target!r}")
            _require(target not in found_targets, f"duplicate bottle target {target!r}")
            found_targets.add(target)
            _require(isinstance(tag, dict), f"{metadata_path.name}: target {target} must be an object")
            public_name, local_name = _expected_paths(version, target)
            _require(tag.get("filename") == public_name, f"{metadata_path.name}: target {target} filename must be {public_name!r}")

            local_value = tag.get("local_filename")
            _require(isinstance(local_value, str) and Path(local_value).name == local_value,
                     f"{metadata_path.name}: target {target} local_filename must be a basename inside the bottle directory")
            _require(local_value == local_name, f"{metadata_path.name}: target {target} local_filename must be {local_name!r}")
            archive = directory / local_value
            _require(archive.parent.resolve() == directory.resolve(), f"{metadata_path.name}: local_filename escapes the bottle directory")
            _require(archive.is_file(), f"{metadata_path.name}: missing archive {local_value}")
            found_archives.add(archive.name)

            checksum = tag.get("sha256")
            _require(isinstance(checksum, str) and re.fullmatch(r"[0-9a-f]{64}", checksum) is not None,
                     f"{metadata_path.name}: target {target} sha256 must be 64 lowercase hexadecimal characters")
            try:
                actual = hashlib.sha256(archive.read_bytes()).hexdigest()
            except OSError as error:
                raise BottleError(f"cannot read bottle archive {local_value}: {error}") from error
            _require(actual == checksum, f"{metadata_path.name}: SHA-256 mismatch for {local_value}")

    _require(found_targets == set(TARGETS), f"expected targets {', '.join(TARGETS)}; found {', '.join(sorted(found_targets)) or 'none'}")
    archive_names = {path.name for path in archives}
    _require(found_archives == archive_names, "found an unreferenced bottle archive")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Homebrew bottle metadata and archives.")
    parser.add_argument("directory", type=Path, help="directory containing the two bottle metadata files and archives")
    parser.add_argument("--version", required=True, help="Perfect Doc release version")
    args = parser.parse_args(argv)
    try:
        validate_bottles(args.directory, args.version)
    except BottleError as error:
        print(f"bottle validation failed: {error}", file=sys.stderr)
        return 1
    print(f"Validated {FORMULA_NAME} {args.version} bottles for {', '.join(TARGETS)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
