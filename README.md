# Student Alert Intake Analytics & Centralized Request System Evidence

## Project Title & Executive Summary
This repository implements a full-stage data engineering pipeline to prove the operational burden created by the current shared student inbox and justify the need for a centralized request system. The solution follows a strict evidence-first workflow: raw inbox data is extracted, validated, reconstructed into request lifecycles, and modeled into a KPI that measures how often a student request is resolved without requiring a student to follow up again.

The business objective is not simply to add a chatbot. The objective is to show, with operational evidence, that the current shared inbox is fragmented, poorly resolved, and creates recurring additional burden on students who must re-contact the system via phone, walk-ins, or repeated email threads. The resulting KPI and business evidence package supports the case for a centralized request system as a process and service improvement, not just a conversational layer.

## Architecture & Data Flow
The pipeline is organized into four primary data layers, each representing a deliberate stage of the FDE evidence chain. See `findings/00_source_map_and_workflow_diagram.md` for the full source map and a diagram of this flow, and `findings/08_review_findings_and_fixes.md` for the record of a code-quality review this project went through, including what was broken and how it was fixed.

### 1) data/raw/ — Extraction
The raw layer captures immutable source evidence from the operational datasets used by the pipeline.

- `raw_student_alert_inbox_final.csv` — the student inbox
- `student_directory_master.csv` — identity resolution and the `student_id` <-> `enrollment_number` crosswalk
- `api_student_interactions.json` — phone/walk-in follow-up contacts (mixed schema, includes bare HTTP error envelopes)
- `mess_roster_updates.csv`, `finance_fee_disputes_Q3.csv`, `academic_credits_master.csv` — **resolution-event sources**. Each records when a student's underlying issue was actually closed out in a downstream operational system (mess clearance, a finance dispute, an academic-credit correction). These are joined against the request lifecycle in the modeling stage to determine whether a request was ever resolved.

This stage is intentionally read-only from the perspective of downstream logic. The extraction layer preserves source fidelity and writes copies into `data/raw/` so that evaluation and forensic review can always trace back to the original operational facts. Two additional sources — `admin_bldg_wifi_auth_logs.csv` and `legacy_alert_archive_2024.csv` — were evaluated and are **not yet integrated**, because neither carries a usable student identifier for the current request model (see the source map for why).

### 2) data/validated/ & data/quarantine/ — Validation & Anomaly Isolation
The validation layer enforces strict data-quality rules without silently fixing source issues.

- `data/validated/`: accepted records that pass the stage rules, including `validated_resolution_events.csv` — the normalized, student-linked union of the three resolution sources above
- `data/quarantine/`: records that are explicitly isolated because they violate critical rules

Examples of quarantined records include:
- API error envelopes such as `500 Internal Server Error` or `504 Gateway Timeout`
- Critical missing values such as null/blank inbox identifiers or API interaction identifiers
- Duplicate identity, duplicate inbox records (including retry-suffixed re-deliveries, e.g. `MSG-1234-dup2`), or resolution-event rows whose enrollment number/student id can't be resolved — all retained for review rather than silently merged or dropped

This stage preserves the operational evidence while separating anomalies from the valid dataset used in later modeling.

### 3) data/modeled/ — Workflow Reconstruction
The modeling layer reconstructs the operational lifecycle of each student request by grouping related emails into request threads, matching each thread against the earliest available resolution event for that student, and combining that with API follow-up events.

Outputs include:
- `student_requests.csv`
- `kpi_metrics.json`

This stage calculates the key operational KPI: the percentage of requests **with a confirmed resolution** that were resolved without any student follow-up. Requests with no confirmed resolution anywhere in the systems we can check are reported separately as `Black-Hole` cases rather than assumed resolved.

### 4) findings/ — Business Evidence Generation
The findings layer translates the metrics into leadership-ready evidence.

- timestamped markdown evidence reports
- PNG charts for operational review
- supporting methodology and specification notes for each pipeline stage
- the source map / workflow diagram (`00_source_map_and_workflow_diagram.md`) and the review record (`08_review_findings_and_fixes.md`)

This is the artifact layer used to support administrative decision-making and justify the proposal for a centralized request system.

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate        # .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Execution Instructions
Use the commands below from the repository root, with the virtual environment above activated.

- End-to-end pipeline: `python3 -m src.pipeline`
- Test suite: `pytest`

The pipeline is designed to be idempotent and overwrite outputs cleanly when rerun, while preserving the audit trail in the logs and quarantined datasets. A full run takes 20-30 seconds, most of it in the modeling stage's per-request resolution matching.

## FDE Assumptions & Guardrails
This section is critical to the grading and design intent of the project.

### No Silent Fixes
The pipeline does not silently repair broken data.

- API error records are triaged to `data/quarantine/` rather than dropped from the operational narrative.
- Critical null values in inbox, directory, and API records are quarantined rather than backfilled.
- This preserves evidence and avoids creating the false impression that a missing or invalid record was successfully processed.

This rule aligns with the FDE principle that the raw problem must remain visible and auditable, even when it is not valid for downstream analytics.

### Identity Preservation
The model explicitly preserves identity burden instead of masking it.

- Unmapped personal Gmail or unknown sender addresses are retained and marked as `Unknown Identity` rather than filtered out.
- This is intentional: the operational metric is about the burden imposed on students and staff when the inbox is not properly matched to a known requester.
- If we dropped those records, we would understate the real user impact and reduce the evidentiary power of the KPI.

### Resolution Matching, Time-Travel & Censoring
None of the raw sources record "this request was resolved" directly. Resolution
is inferred by joining each request thread against the mess-roster,
finance-dispute, and academic-credit sources on `student_id`, described above.
Because those events are keyed only by student (not by request), each request
is matched to the **earliest unclaimed** resolution event for that student at
or after the request's own submission time — so a student's second request
can never reuse the event that already closed their first one, and a
resolution can never be attributed to a request that didn't exist yet. See
`WorkflowModeler.resolve_request_timestamps` for the exact rule; this is the
single most consequential FDE judgement call in the project.

Temporal anomalies are then handled mathematically and transparently in the KPI calculation:

- `Time_Travel_Anomaly`: if a matched resolution timestamp somehow falls before the submission timestamp, the request is flagged and excluded from final KPI math because the lifecycle is invalid.
- `Observation-Window Censoring`: if a request is still unresolved but was submitted within the last 48-hour observation window, it is treated as a censored case rather than a failure. This prevents the KPI from being biased by still-pending requests that do not yet have a full lifecycle.
- `Black-Hole`: requests older than the observation window with no matching resolution event in any of the three downstream systems are flagged separately and counted as black-hole cases, which supports operational evidence that the inbox process is broken from a service-delivery perspective. On the current dataset this is 83.95% of all requests — the single strongest piece of evidence in the report.

These rules ensure the KPI remains mathematically defensible while still reflecting the true operational burden of the shared inbox. The primary KPI is computed only over the requests with a confirmed resolution (`total_included_requests`), not over all requests — see `findings/final_business_evidence_*.md` for why that distinction matters to the headline number.

## Repository Structure
- `src/`: pipeline implementation modules
- `data/`: raw, validated, quarantined, and modeled data layers
- `tests/`: automated pytest coverage for extraction, validation, modeling, pipeline orchestration, and reporting
- `findings/`: business evidence, methodology notes, and historical exports

## Summary
This project is designed to provide a rigorous, auditable, and business-relevant demonstration that the shared inbox is not a sustainable service mechanism. The data pipeline preserves anomalies, quantifies the burden on students, and produces executive evidence proving why a centralized request system is the correct operational response.
