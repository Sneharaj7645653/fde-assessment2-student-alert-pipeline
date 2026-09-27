# 03. Extraction / Ingestion Specification

## Objective
Phase 1 establishes the immutable extraction layer for the data engineering pipeline. The goal is to ingest source data from the raw operational files into the staging area under `data/raw/` without altering the original values, row counts, or source schema. This stage is intentionally limited to retrieval and landing; all validation, cleaning, and type coercion are deferred to later phases.

## Data Sources
- `data/raw_student_alert_inbox_final.csv` — mailbox-style operational inbox export used as the staged inbox source.
- `data/student_directory_master.csv` — official student directory and contact metadata.
- `data/api_student_interactions.json` — mixed-schema API interaction log containing both valid records and bare error envelopes.

## Extraction Logic
1. Centralize all source and output paths in `src/config.py` so the pipeline uses one authoritative configuration layer.
2. Instantiate a `DataExtractor` in `src/extract.py` to read every configured source file without mutating the payload.
3. For CSV inputs, use `pandas.read_csv` and record the extracted row count and column count for completeness verification.
4. For JSON inputs, use `json.load` to preserve raw structure exactly as stored in the source file, including mixed-schema entries and error envelopes.
5. Save untouched copies of the extracted datasets to `data/raw/` as:
   - `raw_inbox.csv`
   - `raw_directory.csv`
   - `raw_api.json`
6. Emit a log statement for each input showing the file name, row count, and shape to prove that the ingest did not silently truncate or drop data.

## Completeness Verification
The extraction stage is designed to prove that data is preserved exactly during ingestion. For each dataset, the pipeline records:
- source path
- row count
- shape (rows, columns)

This provides a basic provenance check that the landing copy matches the original source size and structure at the time of ingestion.

## Out of Scope / Deferred Decisions
- Cleaning and deduplication are intentionally deferred to Phase 2. The objective here is to capture the raw source faithfully, not to alter the historical record.
- HTTP 500/504 error payloads in the JSON are not dropped, transformed, or normalized. They are preserved as raw records because the extraction layer must remain immutable.
- Type coercion, datetime parsing, and value normalization are deferred to Phase 2. Casting within extraction can silently convert or nullify values and hide upstream source drift.
- Schema validation and anomaly resolution are explicitly not part of Phase 1; those decisions belong to downstream quality and validation stages.
