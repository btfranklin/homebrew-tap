class PerfectDoc < Formula
  desc "Check the structure and links in documentation collections"
  homepage "https://github.com/btfranklin/perfect-doc"
  url "https://github.com/btfranklin/perfect-doc/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "69136d1720c42e7001b74fd2ea0c10aa8261b4a7ab03b7d6fdcbd7f2b22bfdf6"
  license "MIT"
  head "https://github.com/btfranklin/perfect-doc.git", branch: "main"

  bottle do
    root_url "https://github.com/btfranklin/homebrew-tap/releases/download/perfect-doc-0.1.0"
    sha256 cellar: :any_skip_relocation, arm64_sequoia: "9479344ac8d3c367dd093fda26215598293f0b2faf8bb1f2b5cb3ee05c5c18b2"
    sha256 cellar: :any,                 x86_64_linux:  "ad65bc239f214b68013a126ef3cfb504a6fdaf1a63edc2b0b092c5aab4155ba1"
  end

  depends_on "rust" => :build

  on_macos do
    depends_on arch: :arm64
  end

  def fetch
    system "cargo", "fetch", *std_cargo_fetch_args
  end

  def install
    system "cargo", "install", *std_cargo_args, "--bin", "perfect-doc"
  end

  test do
    check_command = "#{bin}/perfect-doc check --format json --offline --no-banner"

    valid_docs = testpath/"valid-docs"
    valid_docs.mkpath
    (valid_docs/"README.md").write("# Guide\n\n[Next](next.md)\n")
    (valid_docs/"next.md").write("# Next\n")

    valid_report = JSON.parse(shell_output("#{check_command} #{valid_docs}"))
    assert_equal 2, valid_report.fetch("coverage").fetch("documents")
    assert_equal 2, valid_report.fetch("coverage").fetch("parsed")
    assert_equal false, valid_report.fetch("network_enabled")
    assert_empty valid_report.fetch("diagnostics")

    broken_docs = testpath/"broken-docs"
    broken_docs.mkpath
    (broken_docs/"README.md").write("# Guide\n\n[Missing](missing.md)\n")

    broken_report = JSON.parse(shell_output("#{check_command} #{broken_docs}", 1))
    assert_equal false, broken_report.fetch("network_enabled")
    diagnostic = broken_report.fetch("diagnostics").find do |finding|
      finding.fetch("rule") == "link.exists"
    end
    refute_nil diagnostic
    assert_equal "missing.md", diagnostic.fetch("target")
    assert_match "missing.md", diagnostic.fetch("message")
    assert_match "Create the missing target", diagnostic.fetch("help")
  end
end
