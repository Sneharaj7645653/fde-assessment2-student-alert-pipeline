# Source Map & Workflow / Data Model Diagram

This is the single map of "business question -> source system -> pipeline
stage" for the project, required alongside the code. It reflects the
pipeline as it exists after the review fixes described in
`findings/08_review_findings_and_fixes.md`.

## 1. Business questions -> required information -> source systems

| Business question | Required information | Source system | Format / Retrieval Mode | Owner / grain |
|---|---|---|---|---|
| How much of the shared inbox's request volume actually gets closed out? | Request creation events, resolution events | `data/raw_student_alert_inbox_final.csv`, `data/mess_roster_updates.csv`, `data/finance_fee_disputes_Q3.csv`, `data/academic_credits_master.csv` | CSV / Flat File | Registrar mailbox export; mess office; finance office; academic office. One row per message / clearance / dispute / credit action. |
| Who sent the request, and can we identify them? | Sender identity resolution | `data/student_directory_master.csv` | SQLite Database / SQL Query | Registrar's student master. One row per enrolled student. |
| Did the student have to chase the request again? | Follow-up contact events | `data/api_student_interactions.json` | JSON / File parsing | Phone/walk-in logging system. One row per logged contact attempt. |
| (Not yet integrated — see Known/Unknown) | Independent corroboration of "Walk-in" contacts; pre-2024 ticket history | `data/admin_bldg_wifi_auth_logs.csv`, `data/legacy_alert_archive_2024.csv` | CSV / Flat File | Building WiFi controller (keyed by `mac_address`, no student linkage); legacy archive (keyed by `ticket_ref`, no student linkage). |

`Report Ticketing/Report Ticketing.xlsx` is the public admissions-ticket
dataset used to *synthesize* the inbox (see `generate_raw_student_alert_inbox.py`
and `findings/02_inbox_simulation_spec.md`); it is not itself part of the
runtime pipeline's inputs and is left untouched as a protected source.

## 2. Pipeline data flow

```mermaid
flowchart TD
    subgraph Sources["Client-provided raw sources (never modified)"]
        Inbox["raw_student_alert_inbox_final.csv\n(synthetic student inbox)"]
        Directory["student_directory_master.csv"]
        API["api_student_interactions.json\n(follow-up contacts + error envelopes)"]
        Mess["mess_roster_updates.csv\n(resolution signal)"]
        Finance["finance_fee_disputes_Q3.csv\n(resolution signal)"]
        Academic["academic_credits_master.csv\n(resolution signal)"]
    end

    subgraph Extract["Extraction  (src/extract.py)"]
        FileParse["File Parsing (CSV/JSON)"]
        SQLiteSeed["SQLite Seed & SELECT Query"]
        RawCopy["data/raw/*  (byte-preserving landing copies)"]
    end

    subgraph Validate["Validation & Quarantine  (src/validate.py)"]
        VNulls["Critical-null check\n-> quarantine/critical_nulls.csv"]
        VErr["API error-envelope triage\n-> quarantine/api_errors.json"]
        VDupDir["Directory duplicate check\n-> quarantine/directory_duplicates.json"]
        VDupInbox["Inbox duplicate check (dup-suffix aware)\n-> quarantine/inbox_duplicates.json"]
        VIdentity["Identity resolution -> Unknown Identity"]
        VResEvents["Resolution-event normalization + join key repair\n-> quarantine/resolution_event_nulls.csv"]
        Validated["data/validated/*"]
    end

    subgraph Model["Workflow modeling  (src/model.py)"]
        Thread["Thread emails into Request_ID\n(48h same-sender window)"]
        Resolve["Match each request to the earliest\nunclaimed resolution event for that student"]
        FollowUp["Count API follow-ups between\nsubmission and resolution"]
        KPI["Calculate KPI\n(resolved_without_follow_up_pct)"]
    end

    subgraph Evidence["Evidence  (src/visualize.py)"]
        Report["findings/final_business_evidence_*.md"]
        Chart["findings/kpi_breakdown_*.png"]
    end

    Inbox --> FileParse
    API --> FileParse
    Mess --> FileParse
    Finance --> FileParse
    Academic --> FileParse
    Directory --> SQLiteSeed

    FileParse --> RawCopy
    SQLiteSeed --> RawCopy

    RawCopy --> VNulls --> VErr --> VDupDir --> VDupInbox --> VIdentity --> VResEvents --> Validated

    Validated --> Thread --> Resolve --> FollowUp --> KPI --> Report
    KPI --> Chart
```

## 3. Workflow / entity model

```mermaid
erDiagram
    STUDENT ||--o{ REQUEST : sends
    REQUEST ||--o{ INBOX_MESSAGE : "threaded from"
    REQUEST ||--o{ FOLLOW_UP_CONTACT : "chased via"
    REQUEST |o--o| RESOLUTION_EVENT : "closed by (0 or 1)"

    STUDENT {
        string student_id
        string enrollment_number
        string official_email
    }
    INBOX_MESSAGE {
        string Message_ID
        datetime Timestamp_IST
        string Sender_Email
        bool Has_Attachment
    }
    REQUEST {
        string Request_ID
        datetime Submission_Timestamp
        datetime Resolution_Timestamp
        string Censoring_Status "Resolved | Black-Hole | Observation-Window Censoring"
    }
    FOLLOW_UP_CONTACT {
        string interaction_id
        string interaction_type "Phone Call | Walk-in"
        datetime timestamp_ist
    }
    RESOLUTION_EVENT {
        string source_system "mess_roster | finance_disputes | academic_credits"
        datetime resolution_timestamp
        string resolution_state
    }
```

## 4. Known / Unknown / Assumption / Limitation (source-map level)

- **Known**: the SQLite-extracted directory crosswalk (`student_id` <-> `enrollment_number` <-> `official_email`) provides a reliable SQL-retrieved identity table that lets the three resolution-event sources be joined even though they use three different identifier columns.
- **Known**: resolution events cover roughly 87% of the students who sent a
  request (2,181 of 2,500), so the primary KPI is judgeable for a meaningful
  share of traffic, not a token sample.
- **Unknown / not yet integrated**: `admin_bldg_wifi_auth_logs.csv` has no
  student identifier (only `mac_address`), so it cannot currently corroborate
  "Walk-in" follow-up claims without an additional device-to-student mapping
  that does not exist in this dataset. `legacy_alert_archive_2024.csv` is
  keyed by `ticket_ref`, not `student_id`, and only covers 200 rows from
  March 2024, so it was judged out of scope for the current request
  lifecycle rather than force-joined on a guess.
- **Assumption**: a resolution event is attributed to a student's
  *earliest unclaimed* request at or after that event's timestamp (see the
  docstring on `WorkflowModeler.resolve_request_timestamps`). This is the
  single most consequential judgement call in the model, because these
  events are keyed only by student, not by request.
