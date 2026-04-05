from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess

from repo_first_aid.config import RepoFirstAidConfig, load_config
from repo_first_aid.models import Finding, RuleDefinition, ScanResult

RULES: dict[str, RuleDefinition] = {
    "missing-readme": RuleDefinition(
        "missing-readme",
        "Add a README",
        "high",
        "Most visitors judge a repo from the README first.",
    ),
    "missing-license": RuleDefinition(
        "missing-license",
        "Add a license",
        "medium",
        "A public repo without a license creates reuse uncertainty.",
    ),
    "missing-contributing": RuleDefinition(
        "missing-contributing",
        "Add contributing guidance",
        "medium",
        "Contributors should know how to make changes without guesswork.",
    ),
    "missing-security": RuleDefinition(
        "missing-security",
        "Add a security policy",
        "medium",
        "Security reporting should have a clear path in public repos.",
    ),
    "missing-code-of-conduct": RuleDefinition(
        "missing-code-of-conduct",
        "Add a code of conduct",
        "low",
        "Community expectations help public collaboration feel safe.",
    ),
    "missing-support": RuleDefinition(
        "missing-support",
        "Add a support file",
        "low",
        "People should know where to ask questions instead of opening the wrong issue.",
    ),
    "missing-codeowners": RuleDefinition(
        "missing-codeowners",
        "Add CODEOWNERS",
        "low",
        "Ownership signals make maintenance look more intentional.",
    ),
    "missing-issue-templates": RuleDefinition(
        "missing-issue-templates",
        "Add issue templates",
        "medium",
        "Good issue templates improve signal and reduce back-and-forth.",
    ),
    "missing-pr-template": RuleDefinition(
        "missing-pr-template",
        "Add a PR template",
        "low",
        "PR templates help outside contributors send reviewable changes.",
    ),
    "missing-ci": RuleDefinition(
        "missing-ci",
        "Add CI workflow",
        "medium",
        "Visible automation builds trust that the repo is maintained.",
    ),
    "missing-gitignore": RuleDefinition(
        "missing-gitignore",
        "Add a .gitignore",
        "medium",
        "Ignoring local artifacts prevents accidental junk in public commits.",
    ),
    "template-residue": RuleDefinition(
        "template-residue",
        "Remove template residue",
        "high",
        "Starter copy makes a public repo look unfinished immediately.",
    ),
    "deploy-docs-mismatch": RuleDefinition(
        "deploy-docs-mismatch",
        "Align deployment docs with repo setup",
        "medium",
        "Broken deployment promises are visible trust killers for new users.",
    ),
    "tests-without-tests": RuleDefinition(
        "tests-without-tests",
        "Match test commands with actual tests",
        "medium",
        "A test story that does not exist is worse than an honest one.",
    ),
    "missing-env-example": RuleDefinition(
        "missing-env-example",
        "Add a .env.example",
        "medium",
        "Users should see the required configuration without opening source files.",
    ),
    "frontend-without-screenshot": RuleDefinition(
        "frontend-without-screenshot",
        "Add a frontend screenshot",
        "medium",
        "Public UI repos convert better when visitors can see the product quickly.",
    ),
    "tracked-build-artifacts": RuleDefinition(
        "tracked-build-artifacts",
        "Remove tracked local artifacts",
        "high",
        "Tracked junk makes the repo look messy and can bloat history.",
    ),
}

_ROOT_DOC_FILES = {
    "readme",
    "license",
    "copying",
    "contributing",
    "security",
    "code_of_conduct",
    "code-of-conduct",
    "support",
}

_PLACEHOLDER_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"<\s*your_git_url\s*>",
        r"<\s*your_github_url\s*>",
        r"<\s*your_project_name\s*>",
        r"<\s*your_repo_name\s*>",
        r"replace this readme",
        r"replace the content",
        r"your project description here",
        r"put your project description here",
        r"add your description",
        r"your app name",
        r"insert screenshot",
        r"starter template",
    ]
]

_BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".mp4",
    ".mov",
    ".woff",
    ".woff2",
}

_ENV_PATTERNS = [
    re.compile(r"process\.env\.([A-Z0-9_]+)"),
    re.compile(r"import\.meta\.env\.([A-Z0-9_]+)"),
    re.compile(r"os\.getenv\(\s*[\"']([A-Z0-9_]+)[\"']"),
    re.compile(r"os\.environ\[\s*[\"']([A-Z0-9_]+)[\"']\s*\]"),
]

_IGNORED_ENV_VARS = {"CI", "HOME", "PATH", "PWD", "NODE_ENV", "PORT"}

_TRACKED_JUNK_PREFIXES = (
    "node_modules/",
    ".venv/",
    "venv/",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    "dist/",
    "build/",
    "coverage/",
)

_TRACKED_JUNK_SUFFIXES = (".pyc", ".pyo", ".tsbuildinfo")

_IGNORED_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    ".next",
    ".turbo",
    ".idea",
    ".vscode",
}


@dataclass
class RepositorySnapshot:
    root: Path
    files: list[str]
    tracked_files: set[str]
    config: RepoFirstAidConfig
    _text_cache: dict[str, str]

    def has_file(self, *candidates: str) -> bool:
        wanted = {candidate.lower() for candidate in candidates}
        return any(path.lower() in wanted for path in self.files)

    def find_root_file(self, *names: str) -> str | None:
        wanted = {name.lower() for name in names}
        for path in self.files:
            if "/" in path:
                continue
            stem = Path(path).stem.lower()
            full = path.lower()
            if full in wanted or stem in wanted:
                return path
        return None

    def any_path_startswith(self, prefix: str) -> bool:
        lowered = prefix.lower()
        return any(path.lower().startswith(lowered) for path in self.files)

    def any_path_matches(self, pattern: re.Pattern[str]) -> bool:
        return any(pattern.search(path) for path in self.files)

    def read_text(self, relative_path: str) -> str:
        if relative_path in self._text_cache:
            return self._text_cache[relative_path]
        path = self.root / relative_path
        try:
            if path.suffix.lower() in _BINARY_SUFFIXES:
                text = ""
            elif path.stat().st_size > self.config.max_file_size_bytes:
                text = ""
            else:
                text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        self._text_cache[relative_path] = text
        return text

    def read_root_markdown(self) -> list[tuple[str, str]]:
        docs: list[tuple[str, str]] = []
        for path in self.files:
            if "/" in path:
                continue
            suffix = Path(path).suffix.lower()
            stem = Path(path).stem.lower()
            if suffix in {".md", ".mdx", ".txt"} or stem in _ROOT_DOC_FILES:
                docs.append((path, self.read_text(path)))
        return docs


def list_rules() -> list[RuleDefinition]:
    return sorted(RULES.values(), key=lambda rule: rule.rule_id)


def scan_repository(path: str | Path, config: RepoFirstAidConfig | None = None) -> ScanResult:
    root = Path(path).expanduser().resolve()
    active_config = config or load_config(root)
    snapshot = _build_snapshot(root, active_config)
    findings: list[Finding] = []

    _check_core_files(snapshot, findings)
    _check_templates(snapshot, findings)
    _check_ci_and_repo_hygiene(snapshot, findings)
    _check_placeholder_copy(snapshot, findings)
    _check_deployment_docs(snapshot, findings)
    _check_tests(snapshot, findings)
    _check_env_example(snapshot, findings)
    _check_frontend_visuals(snapshot, findings)
    _check_tracked_artifacts(snapshot, findings)

    filtered = [
        finding
        for finding in findings
        if finding.rule_id not in active_config.ignore_rules
    ]
    filtered.sort(
        key=lambda finding: (
            -_severity_rank(finding.severity),
            finding.rule_id,
            finding.file or "",
        )
    )
    return ScanResult(root=root, findings=filtered)


def _build_snapshot(root: Path, config: RepoFirstAidConfig) -> RepositorySnapshot:
    files: list[str] = []
    for current_root, dirnames, filenames in os.walk(root):
        current_path = Path(current_root)
        rel_dir = current_path.relative_to(root)
        rel_dir_str = "" if rel_dir == Path(".") else rel_dir.as_posix()

        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in _IGNORED_DIR_NAMES
            and not dirname.endswith(".egg-info")
            and not _is_ignored_path(_join_path(rel_dir_str, dirname), config)
        ]

        for filename in filenames:
            rel_path = _join_path(rel_dir_str, filename)
            if _is_ignored_path(rel_path, config):
                continue
            files.append(rel_path)

    tracked_files = _load_tracked_files(root)
    return RepositorySnapshot(
        root=root,
        files=sorted(files),
        tracked_files=tracked_files,
        config=config,
        _text_cache={},
    )


def _check_core_files(snapshot: RepositorySnapshot, findings: list[Finding]) -> None:
    _require_root_file(
        snapshot,
        findings,
        "missing-readme",
        ("README", "README.md", "README.mdx"),
        "Add a `README.md` with setup, purpose, and a quick start.",
    )
    _require_root_file(
        snapshot,
        findings,
        "missing-license",
        ("LICENSE", "LICENSE.md", "COPYING"),
        "Add a license file so reuse terms are explicit.",
    )
    _require_root_file(
        snapshot,
        findings,
        "missing-contributing",
        ("CONTRIBUTING", "CONTRIBUTING.md"),
        "Add `CONTRIBUTING.md` so outside contributors know the workflow.",
    )
    _require_root_file(
        snapshot,
        findings,
        "missing-security",
        ("SECURITY", "SECURITY.md"),
        "Add `SECURITY.md` with supported versions and reporting guidance.",
    )
    _require_root_file(
        snapshot,
        findings,
        "missing-code-of-conduct",
        ("CODE_OF_CONDUCT", "CODE_OF_CONDUCT.md", "CODE-OF-CONDUCT.md"),
        "Add a code of conduct for public collaboration.",
    )
    _require_root_file(
        snapshot,
        findings,
        "missing-support",
        ("SUPPORT", "SUPPORT.md"),
        "Add `SUPPORT.md` so people know where to ask for help.",
    )
    if not snapshot.has_file("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"):
        findings.append(_finding("missing-codeowners", recommendation="Add a `CODEOWNERS` file to show ownership and review paths."))


def _check_templates(snapshot: RepositorySnapshot, findings: list[Finding]) -> None:
    has_issue_template = (
        snapshot.any_path_startswith(".github/ISSUE_TEMPLATE/")
        or snapshot.has_file(".github/ISSUE_TEMPLATE.md", "ISSUE_TEMPLATE.md")
    )
    has_pr_template = snapshot.has_file(
        ".github/PULL_REQUEST_TEMPLATE.md",
        "PULL_REQUEST_TEMPLATE.md",
        "docs/PULL_REQUEST_TEMPLATE.md",
    )
    if not has_issue_template:
        findings.append(
            _finding(
                "missing-issue-templates",
                recommendation="Add one or more issue templates under `.github/ISSUE_TEMPLATE/`.",
            )
        )
    if not has_pr_template:
        findings.append(
            _finding(
                "missing-pr-template",
                recommendation="Add `.github/PULL_REQUEST_TEMPLATE.md` to shape incoming changes.",
            )
        )


def _check_ci_and_repo_hygiene(snapshot: RepositorySnapshot, findings: list[Finding]) -> None:
    has_workflow = any(
        path.lower().startswith(".github/workflows/") and path.lower().endswith((".yml", ".yaml"))
        for path in snapshot.files
    )
    if not has_workflow:
        findings.append(
            _finding(
                "missing-ci",
                recommendation="Add at least one CI workflow under `.github/workflows/`.",
            )
        )
    if not snapshot.has_file(".gitignore"):
        findings.append(
            _finding(
                "missing-gitignore",
                recommendation="Add a `.gitignore` tuned to the stack so local artifacts stay out of the repo.",
            )
        )


def _check_placeholder_copy(snapshot: RepositorySnapshot, findings: list[Finding]) -> None:
    for path, text in snapshot.read_root_markdown():
        if not text:
            continue
        cleaned_text = _strip_markdown_examples(text)
        for pattern in _PLACEHOLDER_PATTERNS:
            match = pattern.search(cleaned_text)
            if match:
                findings.append(
                    _finding(
                        "template-residue",
                        summary=f"{path} still contains starter placeholder text: `{match.group(0)}`",
                        recommendation="Replace starter residue so the repo reads like a finished project.",
                        file=path,
                        evidence=(match.group(0),),
                    )
                )
                return


def _check_deployment_docs(snapshot: RepositorySnapshot, findings: list[Finding]) -> None:
    readme = snapshot.find_root_file("README", "README.md", "README.mdx")
    if not readme:
        return
    readme_text = _strip_markdown_examples(snapshot.read_text(readme)).lower()
    workflow_text = "\n".join(
        snapshot.read_text(path)
        for path in snapshot.files
        if path.lower().startswith(".github/workflows/")
    ).lower()
    package_text = snapshot.read_text("package.json").lower() if snapshot.has_file("package.json") else ""

    mentions_pages = (
        "github.io" in readme_text
        or "gh-pages" in readme_text
        or re.search(
            r"(deploy(?:ed|ment)? to|publish(?:ed)? to|hosted on|live on|available on).{0,40}github pages|github pages.{0,40}(workflow|deploy(?:ed|ment)?|publish(?:ed)?|hosted|live)",
            readme_text,
        )
    )
    mentions_netlify = "netlify.app" in readme_text or re.search(
        r"(deploy(?:ed|ment)? to|publish(?:ed)? to|hosted on|live on|available on).{0,40}netlify|netlify.{0,40}(deploy(?:ed|ment)?|publish(?:ed)?|hosted|live)",
        readme_text,
    )
    mentions_docker = re.search(
        r"(docker compose|docker run|run with docker|deploy with docker)",
        readme_text,
    )

    if mentions_pages and not (
        "pages" in workflow_text or "gh-pages" in package_text
    ):
        findings.append(
            _finding(
                "deploy-docs-mismatch",
                summary="README mentions GitHub Pages, but the repo has no obvious Pages workflow or gh-pages setup.",
                recommendation="Add a Pages workflow or rewrite the README so the deployment path matches reality.",
                file=readme,
                evidence=("GitHub Pages",),
            )
        )
    elif mentions_netlify and not (
        snapshot.has_file("netlify.toml") or "netlify" in workflow_text
    ):
        findings.append(
            _finding(
                "deploy-docs-mismatch",
                summary="README mentions Netlify, but the repo has no `netlify.toml` or Netlify workflow.",
                recommendation="Add the deployment config or remove stale Netlify instructions.",
                file=readme,
                evidence=("Netlify",),
            )
        )
    elif mentions_docker and not (
        snapshot.has_file("Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")
    ):
        findings.append(
            _finding(
                "deploy-docs-mismatch",
                summary="README mentions Docker, but the repo has no Dockerfile or compose file.",
                recommendation="Add the Docker files you document or trim the README instructions.",
                file=readme,
                evidence=("Docker",),
            )
        )


def _check_tests(snapshot: RepositorySnapshot, findings: list[Finding]) -> None:
    if _has_test_files(snapshot):
        return

    package_json = _load_package_json(snapshot)
    pyproject = _load_pyproject(snapshot)
    readme = snapshot.find_root_file("README", "README.md", "README.mdx")
    readme_text = snapshot.read_text(readme).lower() if readme else ""

    package_has_tests = False
    if isinstance(package_json, dict):
        scripts = package_json.get("scripts", {})
        package_has_tests = bool(scripts.get("test"))
    pyproject_has_tests = "pytest" in json.dumps(pyproject).lower()
    readme_has_tests = any(token in readme_text for token in ("pytest", "npm test", "vitest", "pnpm test"))

    if package_has_tests or pyproject_has_tests or readme_has_tests:
        findings.append(
            _finding(
                "tests-without-tests",
                summary="The repo documents or exposes test commands, but no test files were found.",
                recommendation="Add test files or tone down the docs/scripts until the test story is real.",
            )
        )


def _check_env_example(snapshot: RepositorySnapshot, findings: list[Finding]) -> None:
    if snapshot.has_file(".env.example", ".env.sample", ".env.template", ".env.local.example"):
        return

    env_names: set[str] = set()
    for path in snapshot.files:
        if _skip_env_scan(path):
            continue
        suffix = Path(path).suffix.lower()
        if suffix and suffix in _BINARY_SUFFIXES:
            continue
        if suffix not in {"", ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".md", ".json", ".toml", ".yml", ".yaml"}:
            continue
        text = snapshot.read_text(path)
        if not text:
            continue
        for pattern in _ENV_PATTERNS:
            env_names.update(match.group(1) for match in pattern.finditer(text))

    env_names = {name for name in env_names if name not in _IGNORED_ENV_VARS}
    if env_names:
        sample = ", ".join(sorted(env_names)[:4])
        findings.append(
            _finding(
                "missing-env-example",
                summary=f"Environment variables were found in source, but no example env file exists: {sample}",
                recommendation="Add a `.env.example` with placeholders and short variable notes.",
                evidence=tuple(sorted(env_names)),
            )
        )


def _check_frontend_visuals(snapshot: RepositorySnapshot, findings: list[Finding]) -> None:
    if not _looks_like_frontend_repo(snapshot):
        return
    readme = snapshot.find_root_file("README", "README.md", "README.mdx")
    if not readme:
        return
    readme_text = snapshot.read_text(readme)
    if re.search(r"!\[[^\]]*\]\([^)]+\)", readme_text) or re.search(r"<img\s", readme_text, re.IGNORECASE):
        return
    findings.append(
        _finding(
            "frontend-without-screenshot",
            summary="Frontend repo README has no screenshot or image preview.",
            recommendation="Add a screenshot, GIF, or other visual proof to the README.",
            file=readme,
        )
    )


def _check_tracked_artifacts(snapshot: RepositorySnapshot, findings: list[Finding]) -> None:
    if not snapshot.tracked_files:
        return
    offenders = sorted(
        path
        for path in snapshot.tracked_files
        if path.startswith(_TRACKED_JUNK_PREFIXES) or path.endswith(_TRACKED_JUNK_SUFFIXES)
    )
    if not offenders:
        return
    sample = offenders[:5]
    findings.append(
        _finding(
            "tracked-build-artifacts",
            summary="Tracked local or build artifacts were found in git history candidates.",
            recommendation="Untrack generated files and add the right ignore rules before the repo grows further.",
            evidence=tuple(sample),
        )
    )


def _require_root_file(
    snapshot: RepositorySnapshot,
    findings: list[Finding],
    rule_id: str,
    names: tuple[str, ...],
    recommendation: str,
) -> None:
    if not snapshot.find_root_file(*names):
        findings.append(_finding(rule_id, recommendation=recommendation))


def _has_test_files(snapshot: RepositorySnapshot) -> bool:
    for path in snapshot.files:
        name = Path(path).name.lower()
        if path.lower().startswith("tests/"):
            return True
        if name.startswith("test_") or name.endswith("_test.py"):
            return True
        if ".test." in name or ".spec." in name:
            return True
    return False


def _looks_like_frontend_repo(snapshot: RepositorySnapshot) -> bool:
    if snapshot.has_file(
        "vite.config.ts",
        "vite.config.js",
        "next.config.js",
        "next.config.mjs",
        "astro.config.mjs",
        "svelte.config.js",
        "package.json",
    ):
        package_json = _load_package_json(snapshot)
        if not isinstance(package_json, dict):
            return snapshot.has_file("vite.config.ts", "vite.config.js")
        text = json.dumps(package_json).lower()
        return any(
            token in text
            for token in ("react", "next", "vue", "svelte", "astro", "solid-js", "tailwindcss")
        )
    return False


def _load_package_json(snapshot: RepositorySnapshot) -> dict:
    if not snapshot.has_file("package.json"):
        return {}
    try:
        return json.loads(snapshot.read_text("package.json") or "{}")
    except json.JSONDecodeError:
        return {}


def _load_pyproject(snapshot: RepositorySnapshot) -> dict:
    if not snapshot.has_file("pyproject.toml"):
        return {}
    try:
        import tomllib

        return tomllib.loads(snapshot.read_text("pyproject.toml") or "")
    except (ModuleNotFoundError, tomllib.TOMLDecodeError):
        return {}


def _load_tracked_files(root: Path) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            check=False,
        )
    except OSError:
        return set()
    if result.returncode != 0:
        return set()
    return {
        item.decode("utf-8", errors="ignore")
        for item in result.stdout.split(b"\x00")
        if item
    }


def _finding(
    rule_id: str,
    summary: str | None = None,
    recommendation: str = "",
    file: str | None = None,
    evidence: tuple[str, ...] = (),
) -> Finding:
    rule = RULES[rule_id]
    return Finding(
        rule_id=rule.rule_id,
        title=rule.title,
        severity=rule.severity,
        summary=summary or rule.why_it_matters,
        recommendation=recommendation or rule.why_it_matters,
        file=file,
        evidence=evidence,
    )


def _severity_rank(severity: str) -> int:
    return {"low": 1, "medium": 2, "high": 3, "critical": 4}[severity]


def _is_ignored_path(relative_path: str, config: RepoFirstAidConfig) -> bool:
    path = relative_path.strip("/")
    for ignored in config.ignore_paths:
        normalized = ignored.strip("/")
        if not normalized:
            continue
        if path == normalized or path.startswith(f"{normalized}/"):
            return True
    return False


def _join_path(prefix: str, name: str) -> str:
    if not prefix:
        return name
    return f"{prefix}/{name}"


def _strip_markdown_examples(text: str) -> str:
    without_fences = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return re.sub(r"`[^`]+`", "", without_fences)


def _skip_env_scan(path: str) -> bool:
    lowered = path.lower()
    if lowered.startswith(("tests/", "test/", "docs/", ".github/")):
        return True
    name = Path(path).name.lower()
    return ".test." in name or ".spec." in name
