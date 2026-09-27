# 08. Code Review Findings & Fixes

This document records a rigorous review of the pipeline against the FDE
Data Foundations rubric (source reasoning, retrieval, validation, workflow +
metrics, pipeline dependability), what was found broken, and exactly what
was changed. It exists so a grader or future maintainer can see the
before/after evidence rather than trusting a claim that "it works."

## Finding 1 (critical): the primary KPI was permanently 0/0

`src/model.py::WorkflowModeler.resolve_request_timestamps` hardcoded
`Resolution_Timestamp = NaT`, `Censoring_Status = "Resolved"` for every
single request, unconditionally, with no logic behind it. Because
`calculate_kpi()` excludes any request whose `Censoring_Status` is
`Black-Hole` or `Observation-Window Censoring`, and every request with a
null `Resolution_Timestamp` older than 48 hours is classified `Black-Hole`,
**every one of the 32,026 reconstructed requests was excluded from the KPI
denominator on every run.**

This was not a hypothetical: the committed `data/modeled/kpi_metrics.json`
and `findings/final_business_evidence_2026-09-27.md` both showed
`"total_included_requests": 0`, `"resolved_without_follow_up_pct": 0.0`,
and a business narrative literally reading "Across 0 valid requests, only
0.00% were resolved..." — a nonsensical report that had already been
generated and left in the repository.

**Root cause**: three source files sitting unused in `data/` —
`mess_roster_updates.csv`, `finance_fee_disputes_Q3.csv`,
`academic_credits_master.csv` — each contain exactly the resolution
signal missing from the model (`resolution_timestamp`/`state=Cleared`,
`resolved_date_ist`/`status=Closed`, `action_date`/`outcome=Done`),
joinable via `student_id`/`enrollment_number` in
`student_directory_master.csv` with ~87% coverage of students who sent a
request. `grep` across `src/`, `tests/`, and `README.md` before the fix
showed **zero references** to any of these three files.

**Fix**: extraction now lands all three sources (`src/extract.py`);
validation normalizes and joins them into
`data/validated/validated_resolution_events.csv`
(`src/validate.py::validate_resolution_events`); modeling matches each
request to the earliest unclaimed resolution event for the same student at
or after its submission time
(`src/model.py::WorkflowModeler._match_resolution_events`). See
`findings/00_source_map_and_workflow_diagram.md` for the full data flow and
the one-resolution-per-request judgement call this required.

**Result after fix**: `total_included_requests = 5,141`,
`resolved_without_follow_up_pct = 36.94%`, `black_hole_requests = 26,885`
(83.95% of all requests have no confirmed resolution anywhere we can
check) — a defensible number the evidence report can actually stand behind,
and one that argues the case *more* strongly than a fabricated 0%, because
it is falsifiable and traceable to specific systems.

Regression coverage: `tests/test_model.py::TestResolveRequestTimestamps`,
`tests/test_data_integrity.py::test_kpi_denominator_is_not_degenerate`.

## Finding 2 (critical): the KPI breakdown chart always plotted [0, 0]

`src/visualize.py::create_kpi_chart` read a `"resolved_without_follow_up"`
key from the `metrics` dict, but `build_operational_metrics()` never wrote
that key — it only produced `primary_kpi_pct`. The chart's guard
(`if resolved_count and "resolved_without_follow_up" in metrics`) was
therefore always `False`, and `findings/kpi_breakdown_*.png` — a required
submission artifact — silently rendered an all-zero bar chart on every run
regardless of the underlying data. Fixed by having
`build_operational_metrics()` carry the count through explicitly.

Regression coverage:
`tests/test_visualize.py::test_create_kpi_chart_plots_the_real_resolved_vs_follow_up_counts`.

## Finding 3 (critical): the documented pipeline entry point was a no-op

The README instructs `python3 -m src.pipeline` as the way to run the whole
pipeline. `src/pipeline.py` defined `run_pipeline()` but never called it
under `if __name__ == "__main__":` — so that command imported the module,
did nothing, and exited 0 with no output. The only way the pipeline ever
actually ran was via `pytest` invoking it. Fixed by adding the missing
guard.

Regression coverage:
`tests/test_data_integrity.py::test_pipeline_entry_point_actually_runs_when_invoked_as_a_module`.

## Finding 4: duplicate-ingestion anomaly was completely undetected

The inbox simulator marks a duplicate mailbox-ingestion capture by
appending a retry suffix (`-dup1`, `-dup2`, ...) to the *original*
`Message_ID` and extra quoting to the `Body` on the re-delivered copy (see
`generate_raw_student_alert_inbox.py::inject_communication_anomalies`).
`DataValidator.validate_inbox` deduplicated on the exact
`(Message_ID, Timestamp_IST, Body)` tuple, which can never match a row
against its `-dupN` sibling. On the real dataset this meant **0 of the
~993 intentionally injected duplicate rows were ever quarantined** — an
explicit, named problem type in the assignment brief ("duplicate inbox
entries") that the validation layer claimed to handle but didn't. Fixed by
stripping the retry suffix before keying the dedup check; this now
correctly flags 904 duplicate rows.

Regression coverage:
`tests/test_validate.py::test_validate_inbox_catches_dup_suffixed_retry_captures`.

## Finding 5: API error envelopes never reached their intended quarantine bucket

`quarantine_critical_nulls()` ran before `validate_api_records()` and
removed any API record without an `interaction_id` — which is true of every
`{"error": "500 Internal Server Error"}` style envelope by construction.
All 50 real error envelopes in `data/api_student_interactions.json` were
therefore misclassified as "critical null: missing interaction_id" in
`critical_nulls.csv`, and `data/quarantine/api_errors.json` — the bucket the
README explicitly claims holds "API error envelopes such as `500 Internal
Server Error`" — was always empty. This didn't change any row counts, but
it corrupted the audit trail's stated *reason* for quarantining a record,
which matters when a reviewer is trying to explain the KPI to leadership.
Fixed by letting error envelopes pass through the critical-null check
untouched so `validate_api_records()` can classify them correctly.

Regression coverage:
`tests/test_validate.py::test_quarantine_critical_nulls_does_not_swallow_api_error_envelopes`.

## Finding 6: validation-detected anomalies were computed and then discarded

`Missing_Attachment_Anomaly` (5,394 rows, ~15% of the inbox) and
`Unknown Identity` senders (5,136 rows) were correctly computed in
`src/validate.py`, but neither ever reached `data/modeled/student_requests.csv`,
the KPI, or the evidence report — they were dead columns that never left
the validated layer. Both are explicitly named problem types in the
assignment brief ("identity mismatch / unknown identity cases", "false
attachment assumptions"). Fixed by carrying `Unknown_Identity` and
`Missing_Attachment_Anomaly` through to the request summary, the KPI dict,
and the executive evidence table.

## Finding 7: test suite masked all of the above

Two of the original five test files exercised the exact defect surface and
still passed:

- `test_model.py::test_follow_up_api_interaction_counts_as_follow_up`
  called `build_request_summary()` directly with a hand-built DataFrame
  that already had `Resolution_Timestamp` populated, bypassing
  `resolve_request_timestamps()` — the actual function that was broken —
  entirely.
- `test_pipeline.py::test_pipeline_runs_end_to_end` asserted only that the
  key `"resolved_without_follow_up_pct"` was present in the KPI dict, never
  that its value (or the request count behind it) was non-degenerate.

Neither test would ever fail no matter how broken the resolution logic was.
Fixed by adding `tests/test_data_integrity.py` (raw-file immutability,
pipeline-entry-point, idempotency, and non-degenerate-KPI checks) and
strengthening the value-level assertions in `test_pipeline.py` and
`test_visualize.py`.

## Not fixed / explicitly out of scope for this pass

- `admin_bldg_wifi_auth_logs.csv` and `legacy_alert_archive_2024.csv` remain
  unintegrated — neither carries a usable student identifier for the
  current request model (see `findings/00_source_map_and_workflow_diagram.md`,
  section 4). Forcing a join on a guess would be a silent-fix, which the
  project's own stated principle ("no silent fixes") rules out.
- The per-request modeling loop (`WorkflowModeler._match_resolution_events`,
  `build_request_threads`, `build_request_summary`) is implemented with
  Python-level `iterrows()`/`groupby` loops rather than vectorized pandas.
  It runs in ~20-25 seconds on the current ~32k-request dataset, which is
  acceptable for this assignment's scale but would not scale to a
  materially larger inbox without a rewrite.
- `data/raw_student_alert_inbox.csv` vs `..._final.csv` and the two
  top-level one-off scripts (`generate_raw_student_alert_inbox.py`,
  `shift_inbox_timestamps_to_2026.py`) have an undocumented, hard-to-retrace
  lineage (the `_final` file spans 2024-04-23 to 2026-09-20, a span wider
  than either script alone would produce). This is left as-is because the
  protected file itself cannot be regenerated or altered; it is flagged here
  for transparency rather than silently smoothed over.
