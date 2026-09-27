# 05. Workflow Modeling & Metrics Specification

## Objective
Phase 3 reconstructs the student request lifecycle from the validated inbox, directory, and API data and measures the primary KPI: the percentage of Student Alert requests resolved without student follow-up. The purpose is to preserve the operational sequence of the request workflow while explicitly identifying unresolved, censored, and anomalous requests rather than silently discarding them.

## Threading Logic
- Individual emails are grouped by `Sender_Email` into a single `Request_ID` when they occur within 48 hours of each other.
- The first message in each thread becomes the submission anchor, while later messages in the same 48-hour window are treated as follow-on activity in the same request lifecycle.
- Threads are kept distinct when the gap between consecutive emails exceeds 48 hours for the same sender.
- This grouping is intended to reflect the real-world behavior of student support requests, where individual emails may represent the same unresolved issue rather than independent tickets.

## Text Parsing Strategy
- The `Body` field is scanned for `Invisible_Handoff` indicators such as `FWD:`, `FW:`, or `FORWARDED` to detect forwarded or reassigned conversations.
- Financial numbers are extracted from narrative text using regex to capture common malformed amounts such as `50 00`, `Rs. 5,000`, or `₹5000`.
- These parsed annotations are retained for downstream investigations and not silently normalized away, since the raw text is part of the operational evidence.

## KPI Calculation Formula
The KPI measures the share of grouped requests that were resolved without any student-initiated follow-up.

- `Included Requests = valid requests excluding Time_Travel_Anomaly and Censored records`
- `Resolved Without Follow-Up = included requests with Follow_Up_Count = 0`
- `Resolved Without Follow-Up % = (Resolved Without Follow-Up / Included Requests) * 100`

This formula intentionally excludes invalid temporal anomalies and censored cases so the metric reflects only interpretable, complete request lifecycles.

## Handling of Temporal Anomalies (Time Travel & Censoring)
### Time Travel Detection
- If a resolution timestamp exists and is earlier than the corresponding submission timestamp, the request is flagged as `Time_Travel_Anomaly = True`.
- These records are excluded from the final KPI math because they represent impossible or invalid lifecycle sequencing.

### Black-Hole vs Observation-Window Censoring
- `Black-Hole`: overdue or historical requests with no resolution timestamp, indicating a request that appears to have been abandoned or left unresolved.
- `Observation-Window Censoring`: requests submitted within the last 48 hours and thus still legitimately pending at the observation boundary.
- Censored requests are not silently dropped; they are marked and excluded from the final metric calculation to avoid biasing the KPI.

## Output Artifacts
- `data/modeled/student_requests.csv`: reconstructed student request-level lifecycle dataset.
- `data/modeled/kpi_metrics.json`: KPI totals, excluded counts, and percentage value.

## FDE Assumptions
- The model is conservative: it flags anomalies and censoring explicitly instead of making repairs.
- Validation outputs remain the source of truth; Phase 3 consumes only the cleaned stage and avoids re-writing raw operational evidence.
- Follow-up detection is based on API interactions that occur after submission and before resolution, or up to the present when unresolved.
