# B.T. Franklin's Homebrew tap

Homebrew formulas for tools by B.T. Franklin. The tap name is `btfranklin/tap`.

## Available formulas

| Formula | Description |
| --- | --- |
| [Perfect Doc](https://github.com/btfranklin/perfect-doc) | Check the structure and links in Markdown, OKF, and HTML documentation. |

## Install Perfect Doc

Use Homebrew 7 or later. With `btfranklin/tap` added to Homebrew and the Perfect
Doc formula trusted, install with:

```sh
brew install --HEAD perfect-doc
```

The [Perfect Doc formula](Formula/perfect-doc.rb) builds the current `main`
branch from source. Homebrew installs Rust as a build dependency.

See the [Perfect Doc usage guide](https://github.com/btfranklin/perfect-doc/blob/main/docs/usage.md)
for commands, configuration, report formats, and supported checks.

## Contributing

See the [maintenance guide](docs/maintaining.md) for formula checks and tests.

## License

This repository uses the [MIT license](LICENSE). Each formula declares the
license of its source project.
