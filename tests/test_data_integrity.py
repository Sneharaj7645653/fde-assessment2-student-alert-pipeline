"""Pipeline-level guarantees that unit tests on individual functions cannot
catch: that raw source files are never mutated, that a full run is
idempotent, and that the documented entry point actually runs the pipeline.

These are the checks that would have caught the two most severe defects
found in review: `python -m src.pipeline` being a silent no-op (no
`if __name__ == "__main__"` guard), and the primary KPI being permanently
0/0 because every request was excluded from the denominator.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from src.config import (
    ACADEMIC_CREDITS_INPUT,
    API_INTERACTIONS_INPUT,
    FINANCE_DISPUTES_INPUT,
    MESS_ROSTER_INPUT,
    MODELED_KPI_OUTPUT,
    RAW_INBOX_INPUT,
    STUDENT_DIRECTORY_INPUT,
    ROOT_DIR,
)
from src.model import model_all
from src.pipeline import run_pipeline

# The files the assignment explicitly calls out as protected, canonical
# client-provided source data. No pipeline stage may ever write to these.
PROTECTED_SOURCE_FILES = [
    RAW_INBOX_INPUT,
    STUDENT_DIRECTORY_INPUT,
    API_INTERACTIONS_INPUT,
    MESS_ROSTER_INPUT,
    FINANCE_DISPUTES_INPUT,
    ACADEMIC_CREDITS_INPUT,
    ROOT_DIR / "data" / "legacy_alert_archive_2024.csv",
    ROOT_DIR / "data" / "admin_bldg_wifi_auth_logs.csv",
]


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_protected_raw_source_files_are_untouched_by_a_full_pipeline_run() -> None:
    before = {path: _hash_file(path) for path in PROTECTED_SOURCE_FILES}

    run_pipeline()

    after = {path: _hash_file(path) for path in PROTECTED_SOURCE_FILES}
    changed = [str(path) for path in before if before[path] != after[path]]
    assert changed == [], f"Pipeline mutated protected source file(s): {changed}"


def test_pipeline_entry_point_actually_runs_when_invoked_as_a_module() -> None:
    """Regression test for a defect where `python -m src.pipeline` did
    nothing at all: src/pipeline.py defined run_pipeline() but never called
    it under `if __name__ == "__main__"`, so the README's documented run
    command was a silent no-op that produced no logs and no outputs.
    """
    result = subprocess.run(
        [sys.executable, "-m", "src.pipeline"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr
    assert "PIPELINE COMPLETE" in result.stdout + result.stderr


def test_modeling_is_idempotent_across_repeated_runs() -> None:
    first = model_all()["kpi"]
    second = model_all()["kpi"]
    assert first == second


def test_kpi_denominator_is_not_degenerate() -> None:
    """Regression test for the core defect: resolve_request_timestamps()
    used to hardcode Resolution_Timestamp = NaT for every request, which
    made every single request fall into Black-Hole / Observation-Window
    Censoring and get excluded from the KPI. The committed
    data/modeled/kpi_metrics.json showed total_included_requests: 0 and
    resolved_without_follow_up_pct: 0.0 as a result. A healthy run must
    have a non-zero, judgeable population and a percentage that isn't a
    coincidental 0/0.
    """
    kpi = json.loads(Path(MODELED_KPI_OUTPUT).read_text(encoding="utf-8"))
    assert kpi["total_requests"] > 0
    assert kpi["total_included_requests"] > 0
    assert 0.0 <= kpi["resolved_without_follow_up_pct"] <= 100.0
    # Not every request should be an unexplained Black-Hole once resolution
    # events are actually joined in.
    assert kpi["black_hole_requests"] < kpi["total_requests"]
