#!/usr/bin/env python3
"""Verify the public Homebrew bottle and installed Perfect Doc command."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

FORMULA = "btfranklin/tap/perfect-doc"
FORMULA_NAME = "perfect-doc"
TAP_NAME = "btfranklin/tap"
PUBLIC_TAP = "https://github.com/btfranklin/homebrew-tap"
ROOT = Path(__file__).resolve().parents[1]


class VerificationError(RuntimeError):
    """A public install check did not meet its requirement."""


def run(
    command: list[str],
    *,
    capture: bool = False,
    check: bool = True,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        text=True,
        capture_output=capture,
        check=False,
        cwd=cwd,
    )
    if check and result.returncode:
        detail = result.stderr.strip() if capture else ""
        raise VerificationError(
            f"Command failed ({result.returncode}): {' '.join(command)}"
            + (f"\n{detail}" if detail else "")
        )
    return result


def require_clean_homebrew() -> None:
    taps = run(["brew", "tap"], capture=True).stdout.splitlines()
    if TAP_NAME in taps:
        raise VerificationError(f"Runner already has the {TAP_NAME} tap.")

    installed = run(["brew", "list", "--formula", "--versions"], capture=True)
    if any(line.split(maxsplit=1)[0] == FORMULA_NAME for line in installed.stdout.splitlines()):
        raise VerificationError(f"Runner already has an installed {FORMULA_NAME} keg.")


def public_install() -> None:
    run(["brew", "install", "--force-bottle", "--formula", FORMULA])

    tap_path = Path(run(["brew", "--repository", TAP_NAME], capture=True).stdout.strip())
    if tap_path == ROOT or ROOT in tap_path.parents:
        raise VerificationError("Homebrew used the checked-out tap directory.")
    origin = run(
        ["git", "-C", str(tap_path), "remote", "get-url", "origin"],
        capture=True,
    ).stdout.strip().removesuffix(".git")
    if origin != PUBLIC_TAP:
        raise VerificationError(f"Homebrew used an unexpected tap origin: {origin}")

    installed = installed_formula()
    version = installed["versions"]["stable"]
    require_bottle(installed, version)

    executable = Path(run(["brew", "--prefix", FORMULA_NAME], capture=True).stdout.strip())
    executable = executable / "bin" / FORMULA_NAME
    version_result = run([str(executable), "--version"], capture=True)
    expected = f"{FORMULA_NAME} {version}"
    if version_result.stdout.strip() != expected:
        raise VerificationError(
            f"Installed command reported {version_result.stdout.strip()!r}; expected {expected!r}."
        )

    verify_scans(executable)

    run(["brew", "test", "--formula", FORMULA])
    run(["brew", "reinstall", "--force-bottle", "--formula", FORMULA_NAME])
    require_bottle(installed_formula(), version)
    if run([str(executable), "--version"], capture=True).stdout.strip() != expected:
        raise VerificationError("The reinstalled command reports an unexpected version.")
    verify_scans(executable)

    run(["brew", "uninstall", "--formula", FORMULA])
    remaining = run(["brew", "list", "--formula", "--versions"], capture=True)
    if any(line.split(maxsplit=1)[0] == FORMULA_NAME for line in remaining.stdout.splitlines()):
        raise VerificationError(f"Homebrew left the {FORMULA_NAME} keg installed.")


def installed_formula() -> dict:
    result = run(
        ["brew", "info", "--json=v2", "--formula", FORMULA],
        capture=True,
    )
    formulas = json.loads(result.stdout).get("formulae", [])
    if len(formulas) != 1:
        raise VerificationError(f"Expected one installed {FORMULA_NAME} formula.")
    return formulas[0]


def require_bottle(formula: dict, version: str) -> None:
    installed = formula.get("installed", [])
    if len(installed) != 1:
        raise VerificationError(f"Expected one installed {FORMULA_NAME} keg.")
    record = installed[0]
    if record.get("version") != version:
        raise VerificationError(
            f"Installed version {record.get('version')!r} does not match stable {version!r}."
        )
    if record.get("poured_from_bottle") is not True:
        raise VerificationError(f"{FORMULA_NAME} was not poured from a bottle.")


def verify_scans(executable: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="perfect-doc-homebrew-") as directory:
        root = Path(directory)
        (root / "README.md").write_text("# Example\n\nA local document.\n", encoding="utf-8")
        valid = run(
            [str(executable), "check", "README.md", "--offline", "--format", "json"],
            capture=True,
            cwd=root,
        )
        try:
            report = json.loads(valid.stdout)
        except json.JSONDecodeError as error:
            raise VerificationError(f"Valid scan did not return JSON: {error}") from error
        coverage = report.get("coverage", {})
        if coverage.get("documents") != 1 or coverage.get("parsed") != 1:
            raise VerificationError("Valid scan did not select and parse its README.md fixture.")
        if report.get("diagnostics") or report.get("network_enabled") is not False:
            raise VerificationError("Valid offline scan returned diagnostics or enabled the network.")

        (root / "README.md").write_text(
            "# Example\n\n[Missing](missing.md)\n", encoding="utf-8"
        )
        broken = run(
            [str(executable), "check", "README.md", "--offline", "--format", "json"],
            capture=True,
            check=False,
            cwd=root,
        )
        if broken.returncode != 1:
            raise VerificationError(
                f"Broken-link scan returned {broken.returncode}; expected exit code 1."
            )
        try:
            report = json.loads(broken.stdout)
        except json.JSONDecodeError as error:
            raise VerificationError(f"Broken-link scan did not return JSON: {error}") from error

        diagnostic = next(
            (
                item
                for item in report.get("diagnostics", [])
                if item.get("rule") == "link.exists"
                and item.get("target") == "missing.md"
            ),
            None,
        )
        if diagnostic is None:
            raise VerificationError("Broken-link scan did not report link.exists for missing.md.")
        help_text = diagnostic.get("help")
        message = diagnostic.get("message", "")
        location = diagnostic.get("location", {})
        if not isinstance(help_text, str) or "Create the missing target" not in help_text:
            raise VerificationError("Broken-link diagnostic has no actionable repair help.")
        if "missing.md" not in message:
            raise VerificationError("Broken-link diagnostic does not identify missing.md.")
        if (
            location.get("path") != "README.md"
            or location.get("line") != 3
            or not isinstance(location.get("column"), int)
            or location["column"] < 1
        ):
            raise VerificationError("Broken-link diagnostic has no actionable source location.")


def main() -> int:
    try:
        require_clean_homebrew()
        public_install()
    except (OSError, VerificationError, json.JSONDecodeError) as error:
        print(f"Public Homebrew install verification failed: {error}", file=sys.stderr)
        return 1
    print(f"Verified public bottle install, scan, test, reinstall, and removal for {FORMULA_NAME}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
