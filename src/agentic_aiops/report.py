from __future__ import annotations

from .bundle import EvidenceBundle
from .models import VerificationStatus


def render_rca_markdown(bundle: EvidenceBundle) -> str:
    lines = [
        f"# Incident {bundle.incident.incident_id}",
        "",
        f"**Severity:** {bundle.incident.severity}",
        f"**Summary:** {bundle.incident.summary}",
    ]

    if bundle.incident.scope:
        lines.append(f"**Scope:** {bundle.incident.scope}")

    lines.extend(["", "## Evidence", ""])
    for item in bundle.evidence:
        lines.append(
            f"- `{item.evidence_id}` [{item.source}] {item.observation}"
        )

    lines.extend(["", "## Hypotheses", ""])
    for item in bundle.hypotheses:
        marker = {
            VerificationStatus.SUPPORTED: "SUPPORTED",
            VerificationStatus.REJECTED: "REJECTED",
            VerificationStatus.UNVERIFIED: "UNVERIFIED",
        }[item.status]
        evidence = ", ".join(item.evidence_ids) or "none"
        lines.append(
            f"- **{marker}** {item.statement} — evidence: {evidence}"
        )

    return "\n".join(lines) + "\n"
