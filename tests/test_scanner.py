from __future__ import annotations

from pathlib import Path

from repo_first_aid.scanner import scan_repository


def test_scanner_reports_core_missing_files(tmp_path: Path) -> None:
    result = scan_repository(tmp_path)
    rule_ids = {finding.rule_id for finding in result.findings}

    assert "missing-readme" in rule_ids
    assert "missing-license" in rule_ids
    assert "missing-gitignore" in rule_ids


def test_scanner_flags_frontend_without_screenshot_and_env_example(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo app\n", encoding="utf-8")
    (tmp_path / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        """
        {
          "name": "demo-app",
          "scripts": {
            "test": "vitest"
          },
          "dependencies": {
            "react": "^19.0.0"
          }
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.tsx").write_text(
        "const apiKey = import.meta.env.VITE_API_KEY;\n",
        encoding="utf-8",
    )

    result = scan_repository(tmp_path)
    rule_ids = {finding.rule_id for finding in result.findings}

    assert "frontend-without-screenshot" in rule_ids
    assert "missing-env-example" in rule_ids
    assert "tests-without-tests" in rule_ids


def test_scanner_flags_template_residue(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "# Starter\n\nClone with <YOUR_GIT_URL>\n",
        encoding="utf-8",
    )
    result = scan_repository(tmp_path)

    summaries = {finding.rule_id: finding.summary for finding in result.findings}
    assert "template-residue" in summaries
    assert "<YOUR_GIT_URL>" in summaries["template-residue"]


def test_scanner_respects_local_config(tmp_path: Path) -> None:
    (tmp_path / ".repo-first-aid.toml").write_text(
        'ignore_rules = ["missing-readme", "missing-license"]\n',
        encoding="utf-8",
    )
    result = scan_repository(tmp_path)
    rule_ids = {finding.rule_id for finding in result.findings}

    assert "missing-readme" not in rule_ids
    assert "missing-license" not in rule_ids


def test_scanner_ignores_placeholder_examples_in_code_blocks(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "# repo-first-aid\n\n```text\nClone with <YOUR_GIT_URL>\n```\n",
        encoding="utf-8",
    )
    result = scan_repository(tmp_path)
    rule_ids = {finding.rule_id for finding in result.findings}

    assert "template-residue" not in rule_ids


def test_scanner_ignores_env_usage_inside_tests(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_env.py").write_text(
        "value = os.getenv('APP_SECRET')\n",
        encoding="utf-8",
    )
    result = scan_repository(tmp_path)
    rule_ids = {finding.rule_id for finding in result.findings}

    assert "missing-env-example" not in rule_ids


def test_scanner_ignores_generic_deploy_mentions(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "# Repo\n\n- Deployment docs that mention GitHub Pages, Netlify, or Docker without matching setup\n",
        encoding="utf-8",
    )
    result = scan_repository(tmp_path)
    rule_ids = {finding.rule_id for finding in result.findings}

    assert "deploy-docs-mismatch" not in rule_ids
