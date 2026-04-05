from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib


@dataclass
class RepoFirstAidConfig:
    ignore_rules: set[str] = field(default_factory=set)
    ignore_paths: set[str] = field(
        default_factory=lambda: {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "dist",
            "build",
            "coverage",
            ".pytest_cache",
            ".mypy_cache",
            "__pycache__",
        }
    )
    max_file_size_bytes: int = 256_000

    def merged(self, other: "RepoFirstAidConfig") -> "RepoFirstAidConfig":
        return RepoFirstAidConfig(
            ignore_rules=self.ignore_rules | other.ignore_rules,
            ignore_paths=self.ignore_paths | other.ignore_paths,
            max_file_size_bytes=max(self.max_file_size_bytes, other.max_file_size_bytes),
        )


def load_config(root: Path) -> RepoFirstAidConfig:
    config = RepoFirstAidConfig()

    project_config = root / "pyproject.toml"
    if project_config.exists():
        data = _read_toml(project_config)
        tool_data = data.get("tool", {}).get("repo-first-aid", {})
        config = config.merged(_parse_config_block(tool_data))

    local_config = root / ".repo-first-aid.toml"
    if local_config.exists():
        data = _read_toml(local_config)
        config = config.merged(_parse_config_block(data))

    return config


def _read_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _parse_config_block(data: dict) -> RepoFirstAidConfig:
    ignore_rules = {
        str(value).strip()
        for value in data.get("ignore_rules", [])
        if str(value).strip()
    }
    ignore_paths = {
        str(value).strip().strip("/")
        for value in data.get("ignore_paths", [])
        if str(value).strip()
    }
    size_limit = data.get("max_file_size_bytes", 256_000)
    if not isinstance(size_limit, int) or size_limit <= 0:
        size_limit = 256_000
    return RepoFirstAidConfig(
        ignore_rules=ignore_rules,
        ignore_paths=ignore_paths,
        max_file_size_bytes=size_limit,
    )
