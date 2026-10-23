import os
import tempfile
import unittest

from docsdrift.links import check_document_links
from docsdrift.markdown import parse_document


def make_tree(files: dict) -> str:
    root = tempfile.mkdtemp(prefix="docsdrift-test-")
    for rel, content in files.items():
        full = os.path.join(root, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
    return root


class TestCheckLinks(unittest.TestCase):
    def setUp(self):
        self.root = make_tree({
            "docs/guide.md": "# Guide\n\nSee [api](api.md#functions).\n",
            "docs/api.md": "# API\n\n## Functions\n",
        })
        self.cache = {}

    def check(self, relpath, text):
        doc = parse_document(os.path.join(self.root, relpath), text)
        return check_document_links(doc, self.root, self.cache)

    def test_valid_relative_link_and_anchor(self):
        issues = self.check("docs/guide.md", "# Guide\n\nSee [api](api.md#functions).\n")
        self.assertEqual(issues, [])

    def test_broken_link_reports_line_and_suggestion(self):
        issues = self.check("docs/guide.md", "# G\n\nline\n\n[missing](ap1.md)\n")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].line, 5)
        self.assertEqual(issues[0].reason, "target does not exist")
        self.assertIsNotNone(issues[0].suggestion)
        self.assertIn("api.md", issues[0].suggestion)

    def test_broken_anchor_in_target_file(self):
        issues = self.check("docs/guide.md", "[x](api.md#missing-section)\n")
        self.assertEqual(len(issues), 1)
        self.assertIn("anchor", issues[0].reason)

    def test_same_page_anchor(self):
        issues = self.check("docs/guide.md", "# Top\n\n[up](#top) [bad](#nope)\n")
        self.assertEqual(len(issues), 1)
        self.assertIn("#nope", issues[0].reason)

    def test_external_links_are_skipped(self):
        issues = self.check(
            "docs/guide.md",
            "[web](https://example.com) [mail](mailto:a@b.c)\n",
        )
        self.assertEqual(issues, [])

    def test_link_outside_root_is_rejected(self):
        issues = self.check("docs/guide.md", "[esc](../../outside.md)\n")
        self.assertEqual(len(issues), 1)
        self.assertIn("outside the scanned root", issues[0].reason)

    def test_url_encoded_target(self):
        self.root = make_tree({"docs/my file.md": "# Hi\n", "docs/g.md": ""})
        issues = self.check("docs/g.md", "[x](my%20file.md)\n")
        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
