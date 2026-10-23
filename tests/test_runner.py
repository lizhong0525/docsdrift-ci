import os
import unittest

from docsdrift.config import Config
from docsdrift.markdown import CodeBlock
from docsdrift.runner import pr_execution_blocked, run_block, safe_env


def block(code, language="python", info=None):
    return CodeBlock(language=language,
                     info=info or f"{language} docsdrift:run",
                     code=code, line=1)


class TestRunBlock(unittest.TestCase):
    def setUp(self):
        self.config = Config(runtimes={"python": ["python", "-c", "{code}"], "bash": ["bash"]})

    def test_passing_block(self):
        r = run_block(block("print('ok')"), "doc.md", self.config)
        self.assertEqual(r.status, "pass", r.detail)

    def test_failing_block_reports_exit_code_and_output(self):
        r = run_block(block("import sys; print('boom', file=sys.stderr); sys.exit(3)"),
                      "doc.md", self.config)
        self.assertEqual(r.status, "fail")
        self.assertIn("exit code 3", r.detail)
        self.assertIn("boom", r.detail)

    def test_timeout_is_enforced(self):
        r = run_block(block("import time; time.sleep(30)"), "doc.md",
                      self.config, timeout=0.3)
        self.assertEqual(r.status, "timeout")

    def test_unknown_language_is_skipped(self):
        r = run_block(block("puts 1", language="ruby"), "doc.md", self.config)
        self.assertEqual(r.status, "skipped")
        self.assertIn("no runtime configured", r.detail)

    def test_shell_requires_explicit_opt_in(self):
        b = block("echo hi", language="bash")
        r = run_block(b, "doc.md", self.config, allow_shell=False)
        self.assertEqual(r.status, "skipped")
        self.assertIn("opt-in", r.detail)
        r = run_block(b, "doc.md", self.config, allow_shell=True)
        self.assertEqual(r.status, "pass", r.detail)

    def test_missing_runtime_binary_is_a_clean_failure(self):
        cfg = Config(runtimes={"python": ["definitely-not-a-real-runtime-xyz", "-c"]})
        r = run_block(block("print(1)"), "doc.md", cfg)
        self.assertEqual(r.status, "fail")
        self.assertIn("not found", r.detail)


class TestEnvironmentScrubbing(unittest.TestCase):
    def test_safe_env_drops_secrets(self):
        os.environ["DOCSDRIFT_TEST_SECRET"] = "topsecret"
        try:
            self.assertNotIn("DOCSDRIFT_TEST_SECRET", safe_env())
        finally:
            del os.environ["DOCSDRIFT_TEST_SECRET"]

    def test_child_process_cannot_see_parent_secrets(self):
        os.environ["DOCSDRIFT_TEST_SECRET"] = "topsecret"
        try:
            code = ("import os; "
                    "print('LEAKED' if os.environ.get('DOCSDRIFT_TEST_SECRET') else 'clean')")
            cfg = Config(runtimes={"python": ["python", "-c", "{code}"]})
            r = run_block(block(code), "doc.md", cfg)
            self.assertEqual(r.status, "pass", r.detail)
        finally:
            del os.environ["DOCSDRIFT_TEST_SECRET"]


class TestPrTrustGuard(unittest.TestCase):
    def test_pull_request_event_blocks_execution(self):
        env = {"GITHUB_EVENT_NAME": "pull_request"}
        self.assertTrue(pr_execution_blocked(env))
        self.assertFalse(pr_execution_blocked(env, trust_pr=True))

    def test_push_event_allows_execution(self):
        self.assertFalse(pr_execution_blocked({"GITHUB_EVENT_NAME": "push"}))
        self.assertFalse(pr_execution_blocked({}))


if __name__ == "__main__":
    unittest.main()
