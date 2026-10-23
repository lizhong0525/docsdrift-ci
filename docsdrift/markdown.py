"""Minimal Markdown scanning: fenced code blocks, links, and heading anchors.

This is intentionally not a full Markdown parser. It extracts exactly what the
checker needs and ignores links inside code fences / inline code spans so that
example code is not mistaken for real references.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

FENCE_RE = re.compile(
    r"^(?P<indent>[ \t]{0,3})```(?P<info>[^`\n]*)\n(?P<body>.*?)^(?P=indent)```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
LINK_RE = re.compile(
    r"!?\[(?P<text>[^\]\n]*)\]\((?P<target>[^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)"
)
HEADING_RE = re.compile(r"^#{1,6}\s+(?P<title>.+?)\s*#*\s*$", re.MULTILINE)

# Marker a fenced block's info string must contain to be considered runnable.
RUN_MARKER = "docsdrift:run"


@dataclass
class Link:
    target: str
    line: int


@dataclass
class CodeBlock:
    language: str
    info: str
    code: str
    line: int  # 1-based line of the opening fence

    @property
    def runnable(self) -> bool:
        return RUN_MARKER in self.info.split()


@dataclass
class Document:
    path: str
    text: str
    links: list[Link] = field(default_factory=list)
    blocks: list[CodeBlock] = field(default_factory=list)
    anchors: set[str] = field(default_factory=set)


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def github_anchor(title: str) -> str:
    """Approximate GitHub's heading-anchor slugification."""
    slug = title.strip().lower()
    slug = re.sub(r"[^\w\- ]", "", slug, flags=re.UNICODE)
    return slug.replace(" ", "-")


def _blank(text: str, start: int, end: int) -> str:
    """Replace a span with spaces, preserving newlines so line numbers stay valid."""
    return text[:start] + re.sub(r"[^\n]", " ", text[start:end]) + text[end:]


def parse_document(path: str, text: str) -> Document:
    doc = Document(path=path, text=text)

    masked = text
    for m in FENCE_RE.finditer(text):
        info = m.group("info").strip()
        language = info.split()[0].lower() if info else ""
        body = m.group("body")
        indent = m.group("indent")
        if indent:
            # Renderers strip the fence's indentation from the content lines;
            # do the same so examples nested in lists execute correctly.
            body = "\n".join(
                line[len(indent):] if line.startswith(indent) else line
                for line in body.split("\n")
            )
        doc.blocks.append(
            CodeBlock(
                language=language,
                info=info,
                code=body,
                line=_line_of(text, m.start()),
            )
        )
        masked = _blank(masked, m.start(), m.end())

    for m in INLINE_CODE_RE.finditer(masked):
        masked = _blank(masked, m.start(), m.end())

    for m in LINK_RE.finditer(masked):
        doc.links.append(Link(target=m.group("target"), line=_line_of(text, m.start())))

    for m in HEADING_RE.finditer(text):
        doc.anchors.add(github_anchor(m.group("title")))

    return doc
