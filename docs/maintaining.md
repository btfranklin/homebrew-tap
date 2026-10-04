# Maintain the tap

This guide explains how to check formulas and prepare releases.

## Add a formula

Add one Ruby file under `Formula/` for each package. Keep its description,
homepage, license, source, build steps, and useful test in that file. Check the
source project and its release state before you add a URL or checksum.

Run from the repository root. For local work, Homebrew can use this checkout
through a symbolic link. Check `brew --repository btfranklin/tap` first. If the
tap is already registered, use that checkout. Otherwise, run:

```sh
homebrew_tap_path="$(brew --repository)/Library/Taps/btfranklin/homebrew-tap"
mkdir -p "$(dirname "$homebrew_tap_path")"
ln -s "$PWD" "$homebrew_tap_path"
```

Homebrew requires trust before it can execute a local formula. Trust this
formula, then check its metadata, style, and audit results:

```sh
brew trust --formula btfranklin/tap/perfect-doc
brew info --json=v2 --formula btfranklin/tap/perfect-doc
brew style --formula btfranklin/tap/perfect-doc
brew audit --strict --formula btfranklin/tap/perfect-doc
```

After publication, add `--online` to the audit command to check public URLs.

The formula test runs after Homebrew installs the formula. This step uses the
configured Homebrew prefix. On a disposable Homebrew machine, run:

```sh
brew install --build-from-source --HEAD btfranklin/tap/perfect-doc
brew test --HEAD perfect-doc
brew uninstall perfect-doc
```

Use the source and publication status in [the README](../README.md) before
you run an installation.

## Stable releases and bottles

Keep a formula HEAD-only until its public source repository has a stable,
versioned release. Before adding a stable URL, confirm the release archive is
public and calculate its real SHA-256 checksum. Do not use a placeholder
checksum.

Build and test each bottle on its target platform. Confirm that the installed
binary works on that platform. Publish bottle metadata only after Homebrew has
created and uploaded the bottle. Source builds and formula metadata do not prove
that a bottle works.
