"""Local link and file-reference validation.

Only relative (local) links are checked. External URLs (http/https/mailto) are
reported as skipped - DocsDrift never makes network calls. Anchor fragments are
validated against GitHub-style heading slugs of the target Markdown file.
"""

from __future__ import annotations

import difflib
import os
import urllib.parse
from dataclasses import dataclass

from .markdown import Document, parse_document

SKIP_SCHEMES = ("http://", "https://", "mailto:", "tel:")


@dataclass
class LinkIssue:
    path: str
    line: int
    target: str
    reason: str
    suggestion: str | None = None


def _collect_candidates(root: str) -> list[str]:
    candidates = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in filenames:
            full = os.path.join(dirpath, name)
            candidates.append(os.path.relpath(full, root).replace(os.sep, "/"))
    return candidates


def _suggest(target: str, root: str) -> str | None:
    candidates = _collect_candidates(root)
    if not candidates:
        return None
    base = os.path.basename(target)
    by_name = difflib.get_close_matches(
        base, [os.path.basename(c) for c in candidates], n=1, cutoff=0.6
    )
    if by_name:
        for c in candidates:
            if os.path.basename(c) == by_name[0]:
                return c
    by_path = difflib.get_close_matches(target.replace(os.sep, "/"), candidates, n=1, cutoff=0.6)
    return by_path[0] if by_path else None


def check_document_links(doc: Document, root: str, anchor_cache: dict[str, set[str]]) -> list[LinkIssue]:
    issues: list[LinkIssue] = []
    doc_dir = os.path.dirname(os.path.abspath(doc.path))
    root = os.path.abspath(root)

    for link in doc.links:
        target = urllib.parse.unquote(link.target)
        if target.lower().startswith(SKIP_SCHEMES):
            continue

        file_part, _, anchor = target.partition("#")

        if not file_part:
            # Same-page anchor: [text](#section)
            if anchor and anchor not in doc.anchors:
                issues.append(
                    LinkIssue(doc.path, link.line, link.target,
                              f"anchor '#{anchor}' not found in this file")
                )
            continue

        resolved = os.path.normpath(os.path.join(doc_dir, file_part))
        try:
            inside_root = os.path.commonpath(
                [os.path.normcase(resolved), os.path.normcase(root)]
            ) == os.path.normcase(root)
        except ValueError:  # different drives on Windows
            inside_root = False
        if not inside_root:
            issues.append(
                LinkIssue(doc.path, link.line, link.target,
                          "link points outside the scanned root")
            )
            continue
        if not os.path.exists(resolved):
            hint = _suggest(file_part, root)
            issues.append(
                LinkIssue(doc.path, link.line, link.target,
                          "target does not exist",
                          suggestion=f"did you mean '{hint}'?" if hint else None)
            )
            continue

        if anchor and resolved.lower().endswith(".md"):
            if resolved not in anchor_cache:
                try:
                    with open(resolved, encoding="utf-8") as f:
                        anchor_cache[resolved] = parse_document(resolved, f.read()).anchors
                except (OSError, UnicodeDecodeError):
                    anchor_cache[resolved] = set()
            if anchor not in anchor_cache[resolved]:
                issues.append(
                    LinkIssue(doc.path, link.line, link.target,
                              f"anchor '#{anchor}' not found in {os.path.basename(resolved)}")
                )
    return issues
