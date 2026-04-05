from __future__ import annotations

import argparse
from pathlib import Path
import sys

from repo_first_aid.models import SEVERITY_ORDER
from repo_first_aid.reporting import render_json, render_markdown, render_text
from repo_first_aid.scanner import list_rules, scan_repository


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "rules":
        return _run_rules()

    result = scan_repository(args.path)
    if args.format == "json":
        output = render_json(result)
    elif args.format == "markdown":
        output = render_markdown(result)
    else:
        output = render_text(result)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)

    if args.fail_on and result.top_severity:
        if SEVERITY_ORDER[result.top_severity] >= SEVERITY_ORDER[args.fail_on]:
            return 1
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-first-aid",
        description="Audit public repository trust and polish issues.",
    )
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Scan a repository")
    scan_parser.add_argument("path", nargs="?", default=".", help="Path to the repository")
    scan_parser.add_argument(
        "--format",
        choices=("text", "markdown", "json"),
        default="text",
        help="Output format",
    )
    scan_parser.add_argument("--output", help="Write the report to a file")
    scan_parser.add_argument(
        "--fail-on",
        choices=("low", "medium", "high", "critical"),
        help="Exit with code 1 when findings at or above this severity are present",
    )

    subparsers.add_parser("rules", help="List the rule catalog")
    parser.set_defaults(command="scan")
    return parser


def _run_rules() -> int:
    for rule in list_rules():
        sys.stdout.write(f"{rule.rule_id} [{rule.severity}] - {rule.title}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
