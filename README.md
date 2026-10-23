# DocsDrift CI

A GitHub Actions-friendly checker for documentation drift: it validates local links in your Markdown files and re-runs only the code examples that explicitly opt in, so broken examples and dead links fail CI before your users find them. Pure Python standard library — no dependencies.

DocsDrift does **not** try to judge whether your prose is correct. It guarantees two things only: **link integrity** and **reproducible examples**.

## Quickstart

Requires Python 3.10+ (standard library only — nothing to install). DocsDrift
runs straight from a clone, so run it from the repository root (or add the repo
to `PYTHONPATH`); `python -m docsdrift` will not resolve from any other
directory:

```bash
git clone https://github.com/<you>/docsdrift-ci.git
cd docsdrift-ci
python -m docsdrift path/to/docs
```

Exit code is `0` when everything is green, `1` when drift is detected, `2` on usage/config errors.

## Demo walkthrough

The repo ships with intentionally drifted docs under `examples/docs/`:

```bash
python -m docsdrift examples/docs --config docsdrift.example.json
```

Real output:

```
FAIL  link  examples/docs/guide.md:4  [advanced.md#tuning] target does not exist
SKIP  code  examples/docs/guide.md:8  (bash) shell execution requires explicit opt-in (allow_shell / --allow-shell)
PASS  code  examples/docs/guide.md:16  (python)
FAIL  code  examples/docs/guide.md:27  (python) fail
      exit code 1
      ImportError: cannot import name 'deprecated_function' from 'docsdrift' ...
      fix the example at examples/docs/guide.md:27
---
2 file(s), 3 link(s) checked, 1 broken; 3 block(s) run (1 passed, 1 failed), 1 skipped
RESULT: DRIFT DETECTED
```

Every finding reports file, line, failure output, and where to fix it. Use `--format json` for machine consumption.

## How code execution is gated

Executing documentation code is dangerous by default, so v1 stacks four gates:

1. **Per-block opt-in.** Only fenced blocks whose info string contains the `docsdrift:run` marker are executed:

   ````
   ```python docsdrift:run
   print("this runs in CI")
   ```
   ````

2. **Runtime allowlist.** A language runs only if the config maps it to a command. If the command contains `{code}`, the snippet is passed as an argument; otherwise it is fed to the runtime on stdin.
3. **Shell opt-in.** Shell languages (`bash`, `sh`, `cmd`, ...) additionally require `allow_shell: true` in the config or `--allow-shell`.
4. **No secrets, ever.** Executed blocks get a scrubbed environment (PATH, TEMP, little else) — parent-process credentials and tokens are invisible to them. On GitHub Actions `pull_request` events, execution is refused entirely (untrusted code) unless `--trust-pr` is passed; only link checks run.

All runs enforce a timeout (`timeout_seconds`, default 10s).

## Configuration

Place `docsdrift.json` in the directory you run from (or pass `--config`):

```json
{
  "exclude": ["node_modules/**", "vendor/**"],
  "runtimes": {
    "python": ["python", "-c", "{code}"],
    "bash": ["bash"]
  },
  "timeout_seconds": 10,
  "allow_shell": false
}
```

- `exclude` — glob patterns (relative to the working directory) skipped during scans.
- `runtimes` — language → command allowlist. Languages not listed here are reported as skipped, never executed.
- `timeout_seconds` — per-block execution limit.
- `allow_shell` — explicit opt-in for shell-language blocks.

See `docsdrift.example.json` for a working sample.

## GitHub Actions

`.github/workflows/docsdrift.yml` is a ready-to-copy sample. It uses least-privilege permissions (`contents: read`), defines no secrets, and relies on the built-in PR guard so untrusted pull requests get link checks only:

```yaml
permissions:
  contents: read
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
  - run: python -m docsdrift README.md --config docsdrift.example.json
```

## Features

- Recursive Markdown scan with configurable path excludes.
- Local link validation: relative file links, same-page and cross-file `#anchors` (GitHub-style slugs), URL-decoding, root-escape rejection, close-match suggestions ("did you mean ...?").
- External URLs (`https://`, `mailto:`, ...) are reported as skipped — DocsDrift makes no network calls.
- Opt-in code execution with runtime allowlist, shell gating, timeouts, scrubbed environment, and untrusted-PR refusal.
- Reports file, line, captured failure output, and a suggested correction location for every finding.
- Text and JSON output formats; CI-friendly exit codes.

## Known limitations

- Link extraction is regex-based, not a full Markdown parse; exotic link syntax (reference-style links, autolinks) is not checked.
- Anchor slugs approximate GitHub's algorithm; other renderers may differ.
- Each block executes standalone — no shared state between blocks, no working-directory fixture setup.
- `{code}` passed as an argument may hit OS command-line length limits for very large snippets.

## Roadmap

1. Reference-style link and HTML `<a href>` checking.
2. Block setup/teardown hooks and per-block working directory.
3. SARIF output for GitHub code scanning annotations.

## Development

```bash
python -m pytest -q   # 38 tests, pure stdlib, no network
```

## License

MIT — see [LICENSE](LICENSE).
