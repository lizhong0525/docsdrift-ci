"""Command-line interface: python -m docsdrift [paths...]"""

from __future__ import annotations

import argparse
import sys

from .config import ConfigError, load_config
from .core import scan
from .report import to_json, to_text


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="docsdrift",
        description="Check Markdown docs for broken local links and drifting "
                    "(failing) runnable code examples.",
    )
    p.add_argument("paths", nargs="*", default=["."],
                   help="Files or directories to scan (default: current directory)")
    p.add_argument("--config", metavar="FILE",
                   help="Path to config JSON (default: ./docsdrift.json if present)")
    p.add_argument("--execute", dest="execute", action="store_true", default=True,
                   help="Execute blocks marked 'docsdrift:run' (default)")
    p.add_argument("--no-execute", dest="execute", action="store_false",
                   help="Only check links; never execute code")
    p.add_argument("--allow-shell", action="store_true",
                   help="Allow execution of shell-language blocks (bash/sh/cmd/...)")
    p.add_argument("--trust-pr", action="store_true",
                   help="Allow execution even on untrusted pull_request events "
                        "(DANGEROUS: only for trusted code)")
    p.add_argument("--format", choices=["text", "json"], default="text")
    return p


def main(argv: list[str] | None = None) -> int:
    # Reports may contain arbitrary output from executed examples (including
    # undecodable bytes turned into U+FFFD). Never let console encoding turn a
    # report into a UnicodeEncodeError traceback.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as e:
        print(f"docsdrift: {e}", file=sys.stderr)
        return 2
    try:
        report = scan(args.paths, config, execute=args.execute,
                      allow_shell=args.allow_shell, trust_pr=args.trust_pr)
    except FileNotFoundError as e:
        print(f"docsdrift: {e}", file=sys.stderr)
        return 2
    print(to_json(report) if args.format == "json" else to_text(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
