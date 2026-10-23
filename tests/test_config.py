import json
import os
import tempfile
import unittest

from docsdrift.config import ConfigError, load_config


class TestLoadConfig(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="docsdrift-cfg-")

    def write(self, data, name="docsdrift.json"):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(data, str):
                f.write(data)
            else:
                json.dump(data, f)
        return path

    def test_defaults_when_no_file(self):
        cfg = load_config(cwd=self.dir)
        self.assertIn("python", cfg.runtimes)
        self.assertFalse(cfg.allow_shell)
        self.assertGreater(cfg.timeout_seconds, 0)

    def test_valid_config(self):
        path = self.write({
            "exclude": ["vendor/**"],
            "runtimes": {"python": ["python", "-c"]},
            "timeout_seconds": 5,
            "allow_shell": True,
        })
        cfg = load_config(path)
        self.assertTrue(cfg.allow_shell)
        self.assertEqual(cfg.timeout_seconds, 5.0)
        self.assertTrue(cfg.is_excluded("vendor/lib/readme.md"))
        self.assertFalse(cfg.is_excluded("docs/guide.md"))

    def test_invalid_json(self):
        path = self.write("{not json")
        with self.assertRaises(ConfigError):
            load_config(path)

    def test_missing_file(self):
        with self.assertRaises(ConfigError):
            load_config(os.path.join(self.dir, "nope.json"))

    def test_unknown_key_rejected(self):
        path = self.write({"surprise": 1})
        with self.assertRaises(ConfigError):
            load_config(path)

    def test_bad_types_rejected(self):
        for bad in [
            {"exclude": "vendor"},
            {"runtimes": {"python": "python -c"}},
            {"timeout_seconds": -1},
            {"allow_shell": "yes"},
        ]:
            with self.assertRaises(ConfigError, msg=str(bad)):
                load_config(self.write(bad))


if __name__ == "__main__":
    unittest.main()
