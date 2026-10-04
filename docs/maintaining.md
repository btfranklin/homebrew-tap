# Maintain the tap

This guide owns formula checks and bottle publication. The source project owns
its version and release notes. Keep user installation commands in the
[README](../README.md).

## Change a formula

Add one Ruby file under `Formula/` for each package. Keep its description,
homepage, license, source, build steps, and useful test in that file.

Confirm that the source release is public. Download its archive and calculate
its SHA-256 checksum. Use that exact source URL and checksum in the formula.
Do not use a placeholder checksum or a development branch as a stable release.

Make formula changes on `main`. Remove the old bottle block when you change
the source version. From the root of the working checkout, register it as a
local tap if no tap exists. This command
checks the registered path before it runs formula checks. It does not replace
an existing tap:

```sh
(
  set -eu
  checkout_path="$(pwd -P)"
  tap_path="$(brew --repository)/Library/Taps/btfranklin/homebrew-tap"
  if [ ! -e "$tap_path" ] && [ ! -L "$tap_path" ]; then
    mkdir -p "$(dirname "$tap_path")"
    ln -s "$checkout_path" "$tap_path"
  fi
  registered_path="$(cd "$(brew --repository btfranklin/tap)" && pwd -P)"
  if [ "$registered_path" != "$checkout_path" ]; then
    printf '%s\n' "Use the registered tap checkout: $registered_path" >&2
    exit 1
  fi
  brew trust --formula btfranklin/tap/perfect-doc
  brew info --json=v2 --formula btfranklin/tap/perfect-doc
  brew style --formula btfranklin/tap/perfect-doc
  brew audit --strict --online --formula btfranklin/tap/perfect-doc
)
```

If a different tap is registered, change to the reported path and put the
proposed changes there before you run the checks. A published `brew tap` clone
can be used as the working checkout.

On a disposable Homebrew machine, check a source build:

```sh
brew install --build-from-source btfranklin/tap/perfect-doc
brew test perfect-doc
brew uninstall perfect-doc
```

## Build and publish bottles

The [tests workflow](../.github/workflows/tests.yml) uses Homebrew test-bot.
Commit and push the checked formula to `main`. A formula or build workflow
change starts a source build, installed tests, and bottle creation on Apple
Silicon macOS 15 and Linux x64. Use manual dispatch to build another `main`
commit. Both target jobs must pass. Bottle artifacts are kept for 14 days.

Run the bottle validation tests locally with:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

Run the [publication workflow](../.github/workflows/publish.yml) from `main`.
Set `run_id` to the successful build run ID. Leave `publish` false for a
preview. The preview checks the current `main` commit, both target artifacts,
versions, filenames, release URLs, and archive checksums. It prepares the bottle
formula, runs style and audit checks, and prints the formula change.

Set `publish` true to publish. Publication requires an unused release version.
It attests and uploads the tested bottles, commits their checksums, and pushes
the formula directly to `main`. It does not need a branch or pull request, and
it does not build the bottles again. Homebrew's `pr-upload --upload-only`
command uploads files without a pull request.

Do not change tap `main` during publication. The workflow checks that `main`
still points to the tested commit before upload. A later change also prevents
its final push. If publication fails, inspect the release assets and `main`
before recovery. Do not replace an existing bottle release. A new source
version needs a new release version.

After publication, pull `main` into the local checkout. Check the bottle source
URLs, target tags, and checksums in the formula against the public assets.

External actions use moving major version tags. Homebrew's actions use its
`main` branch because that project has date-based releases and no major tags.
Setup selects stable Homebrew updates. Test-bot can use Homebrew development
commands during its checks. The public install workflow updates to stable
Homebrew.

## Check public installation

Run the [public install workflow](../.github/workflows/verify-install.yml).
It uses fresh target runners with no registered tap or installed Perfect Doc.
It installs from the public tap and requires an installed bottle. It checks
version output, valid documents, broken-link repair details, `brew test`, a
bottle reinstall, and uninstall.

A successful source build or formula metadata check does not prove that a
published bottle works. Require the public installation job for each target.

When the next source release is available, test an upgrade from the previous
installed version. Do not claim an upgrade check from a reinstall of the same
version.
