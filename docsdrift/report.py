"""Human-readable and JSON rendering of a ScanReport."""

from __future__ import annotations

import json
import os

from .core import ScanReport


def _rel(path: str) -> str:
    try:
        return os.path.relpath(path).replace(os.sep, "/")
    except ValueError:
        return path


def to_dict(report: ScanReport) -> dict:
    return {
        "ok": report.ok,
        "files_scanned": report.files_scanned,
        "links_checked": report.links_checked,
        "link_issues": [
            {
                "file": _rel(i.path), "line": i.line, "target": i.target,
                "reason": i.reason, "suggestion": i.suggestion,
                "fix_at": f"{_rel(i.path)}:{i.line}",
            }
            for i in report.link_issues
        ],
        "blocks_run": report.blocks_run,
        "block_results": [
            {
                "file": _rel(r.path), "line": r.line, "language": r.language,
                "status": r.status, "detail": r.detail,
                "fix_at": f"{_rel(r.path)}:{r.line}",
            }
            for r in report.block_results
        ],
        "read_errors": report.read_errors,
        "execution_blocked_reason": report.execution_blocked_reason,
    }


def to_json(report: ScanReport) -> str:
    return json.dumps(to_dict(report), indent=2)


def to_text(report: ScanReport) -> str:
    lines: list[str] = []
    if report.execution_blocked_reason:
        lines.append(f"NOTE  {report.execution_blocked_reason}")
    for err in report.read_errors:
        lines.append(f"ERROR {err}")
    for i in report.link_issues:
        lines.append(f"FAIL  link  {_rel(i.path)}:{i.line}  [{i.target}] {i.reason}")
        if i.suggestion:
            lines.append(f"      suggestion: {i.suggestion} (edit {_rel(i.path)}:{i.line})")
    for r in report.block_results:
        if r.status == "pass":
            lines.append(f"PASS  code  {_rel(r.path)}:{r.line}  ({r.language})")
        elif r.status == "skipped":
            lines.append(f"SKIP  code  {_rel(r.path)}:{r.line}  ({r.language}) {r.detail}")
        else:
            lines.append(f"FAIL  code  {_rel(r.path)}:{r.line}  ({r.language}) {r.status}")
            for detail_line in r.detail.splitlines()[:12]:
                lines.append(f"      {detail_line}")
            lines.append(f"      fix the example at {_rel(r.path)}:{r.line}")
    passed = sum(1 for r in report.block_results if r.status == "pass")
    skipped = sum(1 for r in report.block_results if r.status == "skipped")
    lines.append(
        f"---\n{report.files_scanned} file(s), {report.links_checked} link(s) checked, "
        f"{len(report.link_issues)} broken; "
        f"{report.blocks_run} block(s) run ({passed} passed, {len(report.failed_blocks)} failed), "
        f"{skipped} skipped"
    )
    lines.append("RESULT: " + ("OK" if report.ok else "DRIFT DETECTED"))
    return "\n".join(lines)
