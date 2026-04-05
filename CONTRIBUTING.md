# Contributing

Thanks for helping improve `repo-first-aid`.

## What makes a good contribution

- A new rule that catches a real public-repo trust or polish problem
- A false-positive reduction that makes the tool more credible
- Better cross-platform behavior for macOS, Linux, or Windows
- Clearer docs, sample output, or onboarding

## Before you open a PR

1. Run the test suite.
2. Scan the repo itself and make sure your change does not create noisy findings.
3. Keep rules actionable. A finding should tell someone what to fix, not just what went wrong.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
PYTHONPATH=src python -m repo_first_aid scan .
```

On Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
pytest
$env:PYTHONPATH="src"
py -m repo_first_aid scan .
```

## Rule design guidance

- Prefer high-signal heuristics over exhaustive pattern matching.
- Avoid checks that require network access.
- Bias toward issues visible to a GitHub visitor in the first few minutes.
- Add or update tests whenever you change a rule.
