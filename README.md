# B.T. Franklin's Homebrew tap

Homebrew formulas for tools by B.T. Franklin. The tap name is `btfranklin/tap`.

## Available formulas

| Formula | Description |
| --- | --- |
| [perfect-doc](https://github.com/btfranklin/perfect-doc) | Check the structure and links in Markdown, OKF, HTML, and MDX documents. |

## Install Perfect Doc

Use Homebrew 7 or later. Add the tap and trust the formula once:

```sh
brew tap btfranklin/tap
brew trust --formula btfranklin/tap/perfect-doc
```

Then install with the short name:

```sh
brew install perfect-doc
```

You can also add the tap, trust the formula, and install with one command:

```sh
brew install btfranklin/tap/perfect-doc
```

Run a scan from the directory that contains your documents:

```sh
perfect-doc check .
```

See the [Perfect Doc usage guide](https://github.com/btfranklin/perfect-doc/blob/main/docs/usage.md)
for configuration, reports, and test integration.

## Contributing

See [maintain the tap](docs/maintaining.md) for formula checks and bottle
publication.

## License

This repository uses the [MIT license](LICENSE). Each formula installs software
under the license stated by its source project.
