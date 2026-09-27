from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
MODELED_DIR = ROOT_DIR / "data" / "modeled"
KPI_PATH = MODELED_DIR / "kpi_metrics.json"
REQUESTS_PATH = MODELED_DIR / "student_requests.csv"
FINDINGS_DIR = ROOT_DIR / "findings"
DATE_TAG = date.today().strftime("%Y-%m-%d")
EVIDENCE_OUTPUT_PATH = FINDINGS_DIR / f"final_business_evidence_{DATE_TAG}.md"
CHART_OUTPUT_PATH = FINDINGS_DIR / f"kpi_breakdown_{DATE_TAG}.png"


def _default_metric_values() -> dict[str, Any]:
    return {
        "total_valid_requests": 0,
        "resolved_without_follow_up_pct": 0.0,
        "follow_up_pct": 0.0,
        "black_hole_requests": 0,
        "resolved_without_follow_up": 0,
    }


def read_kpi_metrics(kpi_path: str | Path = KPI_PATH) -> dict[str, Any]:
    path = Path(kpi_path)
    if not path.exists():
        return _default_metric_values()

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        return _default_metric_values()
    return payload


def count_black_hole_requests(requests_path: str | Path = REQUESTS_PATH) -> int:
    path = Path(requests_path)
    if not path.exists():
        return 0

    try:
        requests = pd.read_csv(path)
    except Exception:
        return 0

    if "Censoring_Status" not in requests.columns:
        return 0

    return int((requests["Censoring_Status"].fillna("").astype(str).str.strip() == "Black-Hole").sum())


def build_operational_metrics(kpi_metrics: dict[str, Any], black_hole_requests: int) -> dict[str, Any]:
    total_requests = int(kpi_metrics.get("total_requests", 0))
    total_valid_requests = int(kpi_metrics.get("total_included_requests", kpi_metrics.get("total_requests", 0)))
    resolved_without_follow_up = int(kpi_metrics.get("resolved_without_follow_up", 0))
    resolved_pct = float(kpi_metrics.get("resolved_without_follow_up_pct", 0.0))
    follow_up_pct = 0.0
    if total_valid_requests:
        follow_up_requests = total_valid_requests - resolved_without_follow_up
        follow_up_pct = (follow_up_requests / total_valid_requests) * 100.0

    black_hole_pct = (black_hole_requests / total_requests * 100.0) if total_requests else 0.0

    return {
        "total_requests": total_requests,
        "total_valid_requests": total_valid_requests,
        "primary_kpi_pct": resolved_pct,
        "follow_up_pct": round(follow_up_pct, 2),
        "resolved_without_follow_up": resolved_without_follow_up,
        "black_hole_requests": black_hole_requests,
        "black_hole_pct": round(black_hole_pct, 2),
        "excluded_time_travel": int(kpi_metrics.get("excluded_time_travel", 0)),
        "unknown_identity_requests": int(kpi_metrics.get("unknown_identity_requests", 0)),
        "missing_attachment_anomaly_requests": int(kpi_metrics.get("missing_attachment_anomaly_requests", 0)),
    }


def create_kpi_chart(metrics: dict[str, Any], output_path: str | Path = CHART_OUTPUT_PATH) -> Path:
    chart_path = Path(output_path)
    chart_path.parent.mkdir(parents=True, exist_ok=True)

    resolved_count = int(metrics.get("total_valid_requests", 0))
    resolved_no_follow_up_count = int(metrics.get("resolved_without_follow_up", 0))
    follow_up_count = max(resolved_count - resolved_no_follow_up_count, 0)

    labels = ["Resolved without follow-up", "Forced to follow-up"]
    values = [resolved_no_follow_up_count, follow_up_count]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(labels, values, color=["#2E7D32", "#D32F2F"])
    ax.set_ylabel("Request Volume")
    ax.set_title("Student Request Resolution Breakdown")
    ax.set_ylim(0, max(values, default=1) * 1.2 + 1)
    for bar, value in zip(ax.patches, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + max(values, default=1) * 0.02, str(value), ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(chart_path, dpi=200)
    plt.close(fig)
    return chart_path


def generate_business_evidence_report(
    kpi_path: str | Path = KPI_PATH,
    requests_path: str | Path = REQUESTS_PATH,
    output_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> Path:
    kpi_metrics = read_kpi_metrics(kpi_path)
    black_hole_requests = count_black_hole_requests(requests_path)
    metrics = build_operational_metrics(kpi_metrics, black_hole_requests)

    target_dir = Path(output_dir) if output_dir is not None else FINDINGS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    report_name = Path(output_path).name if output_path is not None else f"final_business_evidence_{DATE_TAG}.md"
    output_file = Path(output_dir) / report_name if output_dir is not None and output_path is None else Path(output_path) if output_path is not None else target_dir / f"final_business_evidence_{DATE_TAG}.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    chart_path = target_dir / f"kpi_breakdown_{DATE_TAG}.png"
    create_kpi_chart(metrics, chart_path)

    report_lines = [
        "# Final Business Evidence",
        "",
        "## Executive Summary",
        "",
        f"The current shared inbox is creating avoidable operational friction for students and staff. Of {metrics['total_requests']} total requests reconstructed from the inbox, only {metrics['total_valid_requests']} ({100 - metrics['black_hole_pct']:.2f}%) could be matched to a confirmed resolution event in a downstream system (mess clearance, finance dispute closure, or academic credit action). Among those confirmed requests, {metrics['primary_kpi_pct']:.2f}% were resolved without any student follow-up, meaning {metrics['follow_up_pct']:.2f}% still required the student to chase the issue again through walk-ins or phone calls. The remaining {metrics['black_hole_requests']} requests ({metrics['black_hole_pct']:.2f}% of all requests) have no confirmed resolution anywhere in the operational systems we can check, and are treated as Black-Hole cases rather than assumed resolved.",
        "",
        "The evidence supports replacing the shared inbox with a centralized request system rather than layering an AI chatbot on top of a broken intake process. The core issue is not simply responsiveness; it is the lack of a reliable request lifecycle, no clear ownership, and no auditable resolution path for student requests.",
        "",
        "## Operational Metrics Evidence",
        "",
        "| Metric | Value | Interpretation |",
        "| --- | ---: | --- |",
        f"| Total requests reconstructed | {metrics['total_requests']} | Volume of distinct request threads reconstructed from the inbox |",
        f"| Requests with a confirmed resolution event | {metrics['total_valid_requests']} | Requests matched to a mess/finance/academic closure record, i.e. judgeable for the primary KPI |",
        f"| Percentage resolved with zero student follow-ups | {metrics['primary_kpi_pct']:.2f}% | Primary KPI, computed only over requests with a confirmed resolution |",
        f"| Percentage requiring student follow-up | {metrics['follow_up_pct']:.2f}% | Confirmed requests that forced the student to reinitiate contact via walk-ins or phone calls |",
        f"| Black-Hole requests | {metrics['black_hole_requests']} ({metrics['black_hole_pct']:.2f}%) | Requests with no confirmed resolution in any downstream system; excluded from the primary KPI, reported separately |",
        f"| Requests excluded for time-travel anomalies | {metrics['excluded_time_travel']} | Invalid lifecycle records excluded from final KPI math to preserve accuracy |",
        f"| Requests from an unresolvable sender identity | {metrics['unknown_identity_requests']} | Requests from an address the student directory could not match, compounding the follow-up burden |",
        f"| Requests with a false attachment claim | {metrics['missing_attachment_anomaly_requests']} | Requests that reference an attached document/receipt that was never actually attached |",
        "",
        "![KPI Breakdown](kpi_breakdown_" + DATE_TAG + ".png)",
        "",
        "## Why this supports a centralized request system",
        "",
        "- A centralized request system creates explicit ownership, timestamps, and tracking for each request.",
        "- It prevents the shared inbox from fragmenting the same issue across multiple email threads and repeated outreach.",
        "- It protects the KPI from hidden operational noise such as invalid timestamps and unresolved black-hole cases.",
        "- It creates a measurable service model, which is far more defensible than a chatbot that only responds to messages without fixing the underlying process failure.",
        "",
    ]

    output_file.write_text("\n".join(report_lines), encoding="utf-8")
    return output_file


def main() -> None:
    generate_business_evidence_report()


if __name__ == "__main__":
    main()
