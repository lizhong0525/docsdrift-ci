import io
import json
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout

from docsdrift.cli import main

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class TestCli(unittest.TestCase):
    def test_clean_fixture(self):
        code, out, _ = run_cli(os.path.join(FIXTURES, "clean"))
        self.assertEqual(code, 0, out)
        self.assertIn("RESULT: OK", out)
        self.assertIn("1 block(s) run (1 passed, 0 failed)", out)

    def test_broken_fixture_fails_with_details(self):
        code, out, _ = run_cli(os.path.join(FIXTURES, "broken"))
        self.assertEqual(code, 1, out)
        self.assertIn("RESULT: DRIFT DETECTED", out)
        self.assertIn("guide.md:3", out)          # broken link with line number
        self.assertIn("does-not-exist.md", out)
        self.assertIn("no-such-section", out)     # broken anchor
        self.assertIn("exit code 3", out)         # failing runnable block
        self.assertIn("fix the example at", out)  # suggested correction location

    def test_json_format(self):
        code, out, _ = run_cli(os.path.join(FIXTURES, "broken"), "--format", "json")
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertFalse(data["ok"])
        self.assertEqual(len(data["link_issues"]), 2)
        self.assertTrue(all("fix_at" in i for i in data["link_issues"]))
        failed = [b for b in data["block_results"] if b["status"] == "fail"]
        self.assertEqual(len(failed), 1)

    def test_no_execute_only_checks_links(self):
        code, out, _ = run_cli(os.path.join(FIXTURES, "clean"), "--no-execute")
        self.assertEqual(code, 0, out)
        self.assertIn("0 block(s) run", out)

    def test_missing_path_is_usage_error(self):
        code, _, err = run_cli("definitely-not-here-xyz")
        self.assertEqual(code, 2)
        self.assertIn("not found", err)

    def test_bad_config_is_usage_error(self):
        code, _, err = run_cli("--config", os.path.join(FIXTURES, "broken", "guide.md"))
        self.assertEqual(code, 2)
        self.assertIn("docsdrift:", err)

    def test_pr_event_blocks_execution(self):
        os.environ["GITHUB_EVENT_NAME"] = "pull_request"
        try:
            code, out, _ = run_cli(os.path.join(FIXTURES, "clean"))
        finally:
            del os.environ["GITHUB_EVENT_NAME"]
        self.assertEqual(code, 0, out)
        self.assertIn("untrusted PRs", out)
        self.assertIn("0 block(s) run", out)


if __name__ == "__main__":
    unittest.main()
