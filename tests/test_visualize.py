from pathlib import Path

from src.visualize import (
    build_operational_metrics,
    create_kpi_chart,
    generate_business_evidence_report,
)


def test_generate_business_evidence_report_creates_markdown_file() -> None:
    output_path = Path("findings/final_business_evidence.md")
    report_path = generate_business_evidence_report(output_path=output_path)

    assert report_path.exists()
    assert report_path.suffix == ".md"
    text = report_path.read_text(encoding="utf-8")
    assert "Executive Summary" in text
    assert "Operational Metrics Evidence" in text
    assert "| Metric | Value | Interpretation |" in text
    # A degenerate 0-request report was previously generated and committed
    # to the repo (findings/final_business_evidence_2026-09-27.md showed
    # "Total valid requests processed | 0"); guard against that recurring.
    assert "| Total requests reconstructed | 0 |" not in text


def test_create_kpi_chart_plots_the_real_resolved_vs_follow_up_counts(tmp_path: Path) -> None:
    """Regression test: build_operational_metrics()'s output dict never had
    a "resolved_without_follow_up" key, so create_kpi_chart()'s guard
    `if resolved_count and "resolved_without_follow_up" in metrics` was
    always False and every KPI breakdown PNG ever produced silently plotted
    [0, 0] regardless of the actual data.
    """
    kpi_metrics = {
        "total_requests": 100,
        "total_included_requests": 40,
        "resolved_without_follow_up": 15,
        "resolved_without_follow_up_pct": 37.5,
        "excluded_time_travel": 0,
    }
    metrics = build_operational_metrics(kpi_metrics, black_hole_requests=60)

    assert metrics["resolved_without_follow_up"] == 15

    chart_path = create_kpi_chart(metrics, tmp_path / "chart.png")
    assert chart_path.exists()
    assert chart_path.stat().st_size > 0
