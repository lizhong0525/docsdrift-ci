"""Configuration loading and validation for DocsDrift CI.

Config lives in a JSON file (default: docsdrift.json in the working directory):

{
  "exclude": ["vendor/**", "node_modules/**"],
  "runtimes": {"python": ["python", "-c"], "bash": ["bash"]},
  "timeout_seconds": 10,
  "allow_shell": false
}
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


class ConfigError(Exception):
    pass


DEFAULT_CONFIG_NAME = "docsdrift.json"
DEFAULT_EXCLUDES = [".git/**", "node_modules/**"]
SHELL_LANGUAGES = {"sh", "bash", "shell", "zsh", "powershell", "pwsh", "cmd", "bat"}


@dataclass
class Config:
    exclude: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDES))
    runtimes: dict[str, list[str]] = field(
        default_factory=lambda: {"python": ["python", "-c", "{code}"]}
    )
    timeout_seconds: float = 10.0
    allow_shell: bool = False
    base_dir: str = "."

    def is_excluded(self, relpath: str) -> bool:
        import fnmatch

        rel = relpath.replace(os.sep, "/")
        for pattern in self.exclude:
            if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(os.path.basename(rel), pattern):
                return True
        return False

    def runtime_for(self, language: str) -> list[str] | None:
        return self.runtimes.get(language)


def _validate(data: object, source: str) -> dict:
    if not isinstance(data, dict):
        raise ConfigError(f"{source}: top level must be a JSON object")
    allowed = {"exclude", "runtimes", "timeout_seconds", "allow_shell"}
    unknown = set(data) - allowed
    if unknown:
        raise ConfigError(f"{source}: unknown keys: {', '.join(sorted(unknown))}")
    if "exclude" in data and not (
        isinstance(data["exclude"], list) and all(isinstance(x, str) for x in data["exclude"])
    ):
        raise ConfigError(f"{source}: 'exclude' must be a list of strings")
    if "runtimes" in data:
        rt = data["runtimes"]
        if not isinstance(rt, dict):
            raise ConfigError(f"{source}: 'runtimes' must be an object mapping language to command")
        for lang, cmd in rt.items():
            if not (
                isinstance(lang, str)
                and isinstance(cmd, list)
                and cmd
                and all(isinstance(x, str) for x in cmd)
            ):
                raise ConfigError(
                    f"{source}: runtimes[{lang!r}] must be a non-empty list of strings"
                )
    if "timeout_seconds" in data and not (
        isinstance(data["timeout_seconds"], (int, float)) and data["timeout_seconds"] > 0
    ):
        raise ConfigError(f"{source}: 'timeout_seconds' must be a positive number")
    if "allow_shell" in data and not isinstance(data["allow_shell"], bool):
        raise ConfigError(f"{source}: 'allow_shell' must be a boolean")
    return data


def load_config(path: str | None = None, cwd: str = ".") -> Config:
    cfg = Config(base_dir=os.path.abspath(cwd))
    source = path
    if source is None:
        candidate = os.path.join(cwd, DEFAULT_CONFIG_NAME)
        if os.path.isfile(candidate):
            source = candidate
    if source is None:
        return cfg
    try:
        with open(source, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {source}")
    except OSError as e:
        raise ConfigError(f"cannot read config file {source}: {e}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ConfigError(f"{source}: invalid JSON: {e}")
    data = _validate(data, source)
    if "exclude" in data:
        cfg.exclude = list(DEFAULT_EXCLUDES) + data["exclude"]
    if "runtimes" in data:
        cfg.runtimes = {k.lower(): v for k, v in data["runtimes"].items()}
    if "timeout_seconds" in data:
        cfg.timeout_seconds = float(data["timeout_seconds"])
    if "allow_shell" in data:
        cfg.allow_shell = data["allow_shell"]
    return cfg
