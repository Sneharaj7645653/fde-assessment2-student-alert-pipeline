from pathlib import Path

import pandas as pd

from src.config import MODELED_KPI_OUTPUT, MODELED_REQUESTS_OUTPUT
from src.logger import LOG_PATH
from src.pipeline import DataPipeline


def test_pipeline_runs_end_to_end() -> None:
    pipeline = DataPipeline()
    result = pipeline.run()

    assert result["status"] == "success"
    assert Path(MODELED_KPI_OUTPUT).exists()
    assert Path(MODELED_REQUESTS_OUTPUT).exists()
    assert Path(LOG_PATH).exists()

    kpi = result["modeling"]["kpi"]
    assert isinstance(kpi, dict)
    assert "resolved_without_follow_up_pct" in kpi

    # A key existence check alone previously let a completely degenerate
    # 0/0 KPI (see tests/test_data_integrity.py) pass silently. Assert the
    # metric is actually computed over a real, non-empty population.
    assert kpi["total_requests"] > 0
    assert kpi["total_included_requests"] > 0
    assert 0.0 <= kpi["resolved_without_follow_up_pct"] <= 100.0

    business_evidence_path = Path(result["artifacts"]["business_evidence"])
    assert business_evidence_path.exists(), "pipeline's reported evidence path must be the file it actually wrote"

    requests = pd.read_csv(MODELED_REQUESTS_OUTPUT)
    assert len(requests) == kpi["total_requests"]
    assert not requests["Request_ID"].duplicated().any()


def test_pipeline_run_is_idempotent() -> None:
    first = DataPipeline().run()
    second = DataPipeline().run()

    assert first["modeling"]["kpi"] == second["modeling"]["kpi"]
    assert first["data_shape"] == second["data_shape"]
