# repo-first-aid

`repo-first-aid` catches the public repo mistakes people notice first on GitHub: missing trust files, placeholder README copy, broken deploy claims, tracked junk, thin onboarding, and other "this repo doesn't feel ready" signals.

It is built for maintainers who want a fast local audit before publishing, sharing, or asking for stars.

## Why this exists

Most repo linters care about code quality. `repo-first-aid` cares about first impressions:

- Do you have the files GitHub surfaces in the community profile?
- Does the README still look like a template?
- Are you promising deployment paths without matching config?
- Does the repo look clean to someone opening it on GitHub for the first time?

That gap is where trust gets lost.

## What it catches

- Missing `README`, `LICENSE`, `CONTRIBUTING`, `SECURITY`, `CODE_OF_CONDUCT`, `SUPPORT`, or `CODEOWNERS`
- Missing issue templates, pull request template, CI workflow, or `.gitignore`
- Placeholder README text like `<YOUR_GIT_URL>` and starter residue
- Frontend repos with no screenshot or visual proof in the README
- Test commands without any test files
- Environment variable usage without a `.env.example`
- Deployment docs that mention GitHub Pages, Netlify, or Docker without matching setup
- Tracked junk like `node_modules`, `.venv`, `dist`, `__pycache__`, and `*.tsbuildinfo`

## Install

```bash
python -m pip install repo-first-aid
```

For local development:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

On Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
```

## Usage

Scan the current repo and print a Markdown report:

```bash
repo-first-aid scan .
```

Write JSON output for another tool:

```bash
repo-first-aid scan . --format json --output report.json
```

Fail CI when medium-or-worse findings are present:

```bash
repo-first-aid scan . --fail-on medium
```

List the rule catalog:

```bash
repo-first-aid rules
```

## Config

`repo-first-aid` will look for either:

- `.repo-first-aid.toml`
- `pyproject.toml` under `[tool.repo-first-aid]`

Example:

```toml
ignore_rules = ["missing-support", "missing-codeowners"]
ignore_paths = ["docs/generated", "fixtures"]
```

## Sample report

```text
$ repo-first-aid scan .
repo-first-aid score: 74/100
findings: 4 total | high: 1 | medium: 2 | low: 1

[high] template-residue
README still contains starter placeholder text: <YOUR_GIT_URL>
Fix: Replace starter residue so the repo reads like a finished project.

[medium] frontend-without-screenshot
Frontend repo README has no screenshot or image preview.
Fix: Add a screenshot, GIF, or other visual proof to the README.
```

## Sources

The rule set is grounded in GitHub's own repository health guidance and common public-repo expectations:

- [GitHub docs: repository security quickstart](https://docs.github.com/en/code-security/getting-started/quickstart-for-securing-your-repository)
- [GitHub docs: issue and pull request templates](https://docs.github.com/en/enterprise-server%403.15/communities/using-templates-to-encourage-useful-issues-and-pull-requests)
- [GitHub docs: licensing a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)

More research notes are in [docs/RESEARCH.md](docs/RESEARCH.md).

## License

MIT
