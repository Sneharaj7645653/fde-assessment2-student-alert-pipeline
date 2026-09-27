# 07. Evidence Generation Specification

## Objective
Phase 5 converts the modeled request lifecycle into a concise executive evidence package for Administrative Leadership. The goal is to make the operational failure of the current shared inbox undeniable and to justify a centralized request system as a process improvement rather than a chatbot-only workaround.

## Metric Selection
The evidence report uses a focused set of metrics derived directly from the validated and modeled pipeline:

1. Total valid requests processed.
2. Percentage of requests resolved with zero student follow-ups.
3. Percentage of requests that required follow-up contact from the student.
4. Number of Black-Hole requests that appear unresolved or ignored.
5. Requests excluded due to invalid lifecycle anomalies such as time travel.

These are intentionally limited to a leadership-relevant lens: service quality, student burden, and operational reliability.

## Executive Summary Logic
The narrative is deliberately simple: when a large share of requests require the student to chase the office again, the problem is not just communication quality. It is a broken intake and tracking process. The dashboard makes this visible by combining the KPI outcome with the volume of unresolved cases and the student burden imposed by repeated follow-up.

Each daily run produces timestamped artifacts such as `findings/final_business_evidence_YYYY-MM-DD.md` and `findings/kpi_breakdown_YYYY-MM-DD.png`, which supports historical tracking and preserves a clean evidence trail for leadership review.

## Operational Metrics Evidence Table
The Markdown table is shaped to be readable by senior administrators and to show the exact tradeoff between successful resolutions and re-triggered follow-up.

- `Primary KPI`: the zero-follow-up rate is the most important measure of whether the current process actually resolves requests.
- `Follow-up rate`: this quantifies the burden placed on the student to re-engage the system manually.
- `Black-Hole count`: this highlights requests that disappeared from operational oversight and were never meaningfully resolved.
- `Time-travel exclusions`: these are excluded from the KPI math to preserve analytical integrity and avoid false improvements from invalid records.

## Why this supports a centralized request system
This evidence does not argue for a chatbot as a primary fix. A chatbot can route messages, but it does not repair the underlying process failure: no ownership, no request lifecycle tracking, and no consistent resolution accountability.

A centralized request system provides:

- a single, auditable queue for each request,
- explicit ownership and timestamps,
- a clear resolution path rather than hidden email threads,
- measurable service quality for administration and leadership reporting.

That is why the final business evidence emphasizes process failure and service burden rather than conversational convenience. The evidence supports a centralized, accountable system for managing requests end-to-end, which is the practical foundation required for any downstream AI assistance.
