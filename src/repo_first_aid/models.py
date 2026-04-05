from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

Severity = Literal["low", "medium", "high", "critical"]

SEVERITY_ORDER: dict[Severity, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}

SEVERITY_PENALTIES: dict[Severity, int] = {
    "critical": 30,
    "high": 18,
    "medium": 10,
    "low": 4,
}


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    title: str
    severity: Severity
    why_it_matters: str


@dataclass(frozen=True)
class Finding:
    rule_id: str
    title: str
    severity: Severity
    summary: str
    recommendation: str
    file: str | None = None
    evidence: tuple[str, ...] = ()


@dataclass
class ScanResult:
    root: Path
    findings: list[Finding]
    scanned_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    @property
    def score(self) -> int:
        penalty = sum(SEVERITY_PENALTIES[finding.severity] for finding in self.findings)
        return max(0, 100 - penalty)

    @property
    def counts(self) -> dict[Severity, int]:
        counts: dict[Severity, int] = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        for finding in self.findings:
            counts[finding.severity] += 1
        return counts

    @property
    def top_severity(self) -> Severity | None:
        if not self.findings:
            return None
        ordered = sorted(
            self.findings,
            key=lambda finding: SEVERITY_ORDER[finding.severity],
            reverse=True,
        )
        return ordered[0].severity
