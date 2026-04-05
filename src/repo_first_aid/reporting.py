from __future__ import annotations

import json

from repo_first_aid.models import Finding, ScanResult


def render_markdown(result: ScanResult) -> str:
    counts = result.counts
    lines = [
        f"# repo-first-aid report for `{result.root.name}`",
        "",
        f"- Score: **{result.score}/100**",
        f"- Findings: **{len(result.findings)}**",
        f"- Breakdown: critical {counts['critical']}, high {counts['high']}, medium {counts['medium']}, low {counts['low']}",
        "",
    ]

    if not result.findings:
        lines.append("No findings. This repo looks healthy from a public-first-impression standpoint.")
        return "\n".join(lines)

    for severity in ("critical", "high", "medium", "low"):
        severity_findings = [finding for finding in result.findings if finding.severity == severity]
        if not severity_findings:
            continue
        lines.append(f"## {severity.title()}")
        lines.append("")
        for finding in severity_findings:
            lines.extend(_render_markdown_finding(finding))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_text(result: ScanResult) -> str:
    counts = result.counts
    lines = [
        f"repo-first-aid score: {result.score}/100",
        (
            f"findings: {len(result.findings)} total | "
            f"critical: {counts['critical']} | high: {counts['high']} | "
            f"medium: {counts['medium']} | low: {counts['low']}"
        ),
        "",
    ]
    if not result.findings:
        lines.append("No findings. This repo looks healthy from a public-first-impression standpoint.")
        return "\n".join(lines)

    for finding in result.findings:
        lines.append(f"[{finding.severity}] {finding.rule_id}")
        lines.append(finding.summary)
        lines.append(f"Fix: {finding.recommendation}")
        if finding.file:
            lines.append(f"File: {finding.file}")
        if finding.evidence:
            lines.append(f"Evidence: {', '.join(finding.evidence)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_json(result: ScanResult) -> str:
    payload = {
        "repository": str(result.root),
        "name": result.root.name,
        "scanned_at": result.scanned_at,
        "score": result.score,
        "counts": result.counts,
        "findings": [
            {
                "rule_id": finding.rule_id,
                "title": finding.title,
                "severity": finding.severity,
                "summary": finding.summary,
                "recommendation": finding.recommendation,
                "file": finding.file,
                "evidence": list(finding.evidence),
            }
            for finding in result.findings
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _render_markdown_finding(finding: Finding) -> list[str]:
    lines = [f"### `{finding.rule_id}`", ""]
    lines.append(f"**Why it matters:** {finding.summary}")
    lines.append("")
    lines.append(f"**Fix:** {finding.recommendation}")
    if finding.file:
        lines.append("")
        lines.append(f"**File:** `{finding.file}`")
    if finding.evidence:
        lines.append("")
        lines.append("**Evidence:**")
        for item in finding.evidence:
            lines.append(f"- `{item}`")
    lines.append("")
    return lines
