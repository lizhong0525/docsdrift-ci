import unittest

from docsdrift.markdown import github_anchor, parse_document


class TestParseDocument(unittest.TestCase):
    def test_extracts_links_blocks_anchors(self):
        text = (
            "# Hello World\n"
            "\n"
            "See [other](other.md#section-one) and [ext](https://example.com).\n"
            "\n"
            "```python docsdrift:run\n"
            "print('hi')\n"
            "```\n"
            "\n"
            "```bash\n"
            "echo nope\n"
            "```\n"
        )
        doc = parse_document("doc.md", text)
        self.assertEqual(len(doc.links), 2)
        self.assertEqual(doc.links[0].target, "other.md#section-one")
        self.assertEqual(doc.links[0].line, 3)
        self.assertEqual(len(doc.blocks), 2)
        self.assertTrue(doc.blocks[0].runnable)
        self.assertEqual(doc.blocks[0].language, "python")
        self.assertEqual(doc.blocks[0].line, 5)
        self.assertFalse(doc.blocks[1].runnable)
        self.assertIn("hello-world", doc.anchors)

    def test_links_inside_code_fences_are_ignored(self):
        text = "```python\nx = '[not a link](nope.md)'\n```\n"
        doc = parse_document("doc.md", text)
        self.assertEqual(doc.links, [])

    def test_links_inside_inline_code_are_ignored(self):
        doc = parse_document("doc.md", "run `[fake](fake.md)` please\n")
        self.assertEqual(doc.links, [])

    def test_indented_fence_body_is_dedented(self):
        text = "1. item\n\n   ```python docsdrift:run\n   print('hi')\n   ```\n"
        doc = parse_document("doc.md", text)
        self.assertEqual(len(doc.blocks), 1)
        self.assertEqual(doc.blocks[0].code, "print('hi')\n")

    def test_empty_and_malformed_input(self):
        doc = parse_document("empty.md", "")
        self.assertEqual(doc.links, [])
        self.assertEqual(doc.blocks, [])
        # Unclosed fence: no block extracted, no crash.
        doc = parse_document("bad.md", "```python\nprint(1)\n")
        self.assertEqual(doc.blocks, [])


class TestGithubAnchor(unittest.TestCase):
    def test_slugification(self):
        self.assertEqual(github_anchor("Hello, World!"), "hello-world")
        self.assertEqual(github_anchor("Step 2: Install & Run"), "step-2-install--run")


if __name__ == "__main__":
    unittest.main()
