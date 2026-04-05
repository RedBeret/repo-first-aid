from __future__ import annotations

import json
from pathlib import Path

from repo_first_aid.cli import main


def test_cli_writes_json_report(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Good repo\n", encoding="utf-8")
    (tmp_path / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(".venv/\n", encoding="utf-8")
    output_path = tmp_path / "report.json"

    exit_code = main(["scan", str(tmp_path), "--format", "json", "--output", str(output_path)])

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["name"] == tmp_path.name
    assert "findings" in payload


def test_cli_fail_on_high(tmp_path: Path) -> None:
    exit_code = main(["scan", str(tmp_path), "--fail-on", "high"])
    assert exit_code == 1
