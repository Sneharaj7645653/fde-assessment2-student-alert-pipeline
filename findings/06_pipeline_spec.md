# 06. Pipeline Automation Specification

## Pipeline Architecture
Phase 4 orchestrates the previously validated stages in a strict sequential flow:

1. Extraction: copies the raw operational datasets into the immutable raw landing zone.
2. Validation: applies schema, identity, anomaly, and quarantine rules without modifying the source data.
3. Modeling: reconstructs the request lifecycle, joins API follow-up data, and calculates the KPI.

The orchestrator sits above the stage modules and is responsible for lifecycle control, telemetry, and error boundary enforcement.

## Idempotency Guarantees
- Each phase overwrites existing outputs instead of appending.
- Raw stage files are re-created on every pipeline run, ensuring consistent row counts and no duplicate records.
- Validated outputs are written to fixed destinations and replaced in-place.
- Modeled outputs are also overwritten, which preserves deterministic results when the pipeline is re-executed.
- The pipeline log file is rewritten per run to avoid stale audit trails.

## Error Handling
- Extraction is treated as the entry gate. If extraction fails, validation and modeling do not run.
- Validation is the second gate. If validation fails, modeling does not execute.
- Errors are captured with `try/except` blocks and re-raised as `RuntimeError` instances that preserve the exact failure context.
- The logger records the phase name and exception stack trace so the point of failure is auditable.

## Telemetry and Data Shape Auditing
The logger emits both console and file output to `data/pipeline.log`.

It records:
- the start and end of each phase,
- phase-level success/failure events,
- row-count and shape changes between the raw, validated, and modeled datasets.

This makes it possible to answer questions such as:
- how many records were quarantined during validation,
- whether modeling reduced or expanded the request set,
- whether a stage introduced unexpected data drift.

The purpose of this audit trail is to preserve evidence of data transformations without silently modifying records.
