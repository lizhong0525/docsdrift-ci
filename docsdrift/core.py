"""Scan orchestration: find Markdown files, run link and code checks, report."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .config import Config
from .links import LinkIssue, check_document_links
from .markdown import parse_document
from .runner import RunResult, pr_execution_blocked, run_block


@dataclass
class ScanReport:
    files_scanned: int = 0
    links_checked: int = 0
    link_issues: list[LinkIssue] = field(default_factory=list)
    blocks_run: int = 0
    block_results: list[RunResult] = field(default_factory=list)
    read_errors: list[str] = field(default_factory=list)
    execution_blocked_reason: str | None = None

    @property
    def failed_blocks(self) -> list[RunResult]:
        return [r for r in self.block_results if r.status in ("fail", "timeout")]

    @property
    def ok(self) -> bool:
        return not self.link_issues and not self.failed_blocks and not self.read_errors


def _try_relpath(path: str, start: str) -> str | None:
    try:
        return os.path.relpath(path, start)
    except ValueError:  # different drives on Windows
        return None


def find_markdown_files(paths: list[str], config: Config) -> list[str]:
    found: list[str] = []
    for p in paths:
        if not os.path.exists(p):
            raise FileNotFoundError(f"scan path not found: {p}")
        if os.path.isfile(p):
            if p.lower().endswith((".md", ".markdown")):
                found.append(os.path.abspath(p))
            continue
        for dirpath, dirnames, filenames in os.walk(p):
            rel_dir = _try_relpath(dirpath, config.base_dir)
            if rel_dir is not None:
                dirnames[:] = [
                    d for d in dirnames
                    if not config.is_excluded(os.path.join(rel_dir, d)) and not d.startswith(".")
                ]
            else:
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for name in filenames:
                if not name.lower().endswith((".md", ".markdown")):
                    continue
                full = os.path.join(dirpath, name)
                rel = _try_relpath(full, config.base_dir)
                if rel is not None and config.is_excluded(rel):
                    continue
                found.append(os.path.abspath(full))
    return sorted(set(found))


def _containing_root(path: str, roots: list[str]) -> str:
    """The scan root a file belongs to: the scanned directory it was found under
    (or the parent directory of an explicitly scanned file)."""
    norm = os.path.normcase(os.path.abspath(path))
    for root in roots:
        try:
            if os.path.commonpath([norm, os.path.normcase(root)]) == os.path.normcase(root):
                return root
        except ValueError:  # different drives on Windows
            continue
    return os.path.dirname(os.path.abspath(path))


def scan(paths: list[str], config: Config, execute: bool = True,
         allow_shell: bool = False, trust_pr: bool = False) -> ScanReport:
    report = ScanReport()
    files = find_markdown_files(paths, config)
    roots = [
        os.path.abspath(p) if os.path.isdir(p)
        else os.path.dirname(os.path.abspath(p))
        for p in paths
    ]
    anchor_cache: dict[str, set[str]] = {}

    if execute and pr_execution_blocked(trust_pr=trust_pr):
        execute = False
        report.execution_blocked_reason = (
            "GitHub Actions pull_request event detected: refusing to execute code from "
            "untrusted PRs (re-run with --trust_pr/--trust-pr only on trusted code)"
        )

    for path in files:
        report.files_scanned += 1
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError) as e:
            report.read_errors.append(f"{path}: cannot read as UTF-8 text: {e}")
            continue

        doc = parse_document(path, text)
        report.links_checked += len(doc.links)
        root = _containing_root(path, roots)
        report.link_issues.extend(check_document_links(doc, root, anchor_cache))

        for block in doc.blocks:
            if not block.runnable:
                continue
            if not execute:
                report.block_results.append(
                    RunResult(path, block.line, block.language, "skipped",
                              report.execution_blocked_reason or "execution disabled")
                )
                continue
            report.blocks_run += 1
            report.block_results.append(
                run_block(block, path, config, allow_shell=allow_shell)
            )
    return report
