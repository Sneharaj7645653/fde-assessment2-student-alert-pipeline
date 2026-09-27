# Dataset Reconnaissance

## 1. Purpose

This document is the first evidence-based artifact for the Report Ticketing assignment. The goal is to establish what the repository currently contains, what the actual workbook evidence supports, and what remains uncertain before any specification or implementation work begins.

This reconnaissance does not transform data, clean data, create a pipeline, or assume a final business metric. It focuses only on repository inspection and workbook verification.

---

## 2. Repository/Data Scope

### Observed repository contents

The workspace contains:

- `data/` — a synthetic dataset folder with files such as CSV/JSON reference data
- `Report Ticketing/` — the selected project/data source for the current assignment

### Important scope constraint

The selected source for this assignment is the `Report Ticketing` folder. The files under `data/` are not treated as the primary project dataset unless the evidence later shows they are explicitly relevant.

### Evidence from repository materials

| Item | Status | Observed | Documented | Inferred | Unknown |
|---|---|---|---|---|---|
| `Report Ticketing/Readme.md` | Documented | Does not describe a ticketing system | Describes an Indonesian higher-education QA dataset | README appears unrelated to the Excel workbook | Whether README is stale or unrelated |
| `Report Ticketing/Annotation.md` | Documented | Does not describe ticket workflow data | Describes annotation rules for a QA dataset | Annotation materials are not aligned with workbook schema | Whether these files are accidental or placeholder docs |
| `Report Ticketing/Report Ticketing.xlsx` | Observed | Single-sheet workbook with 59,074 rows and 15 columns | No explicit schema documentation inside the workbook | Likely operational ticket/intake dataset | Exact business glossary and source-system definition |
| `data/` folder | Observed | Synthetic reference datasets | Not identified as the project source | Likely not part of the primary assignment scope | Whether any file is intentionally linked later |

### Key finding

The repository metadata and the workbook contents do not align. The README and annotation files describe a QA/text dataset, while the workbook contains operational ticket-like records. This discrepancy is material and must be treated as a data-source uncertainty rather than ignored.

---

## 3. Source Inventory

### Source inventory table

| Filename | Format | Purpose, if explicitly known | Number of sheets | Observed rows | Observed columns | Grain | Likely entity | Status |
|---|---|---|---:|---:|---:|---|---|---|
| `Report Ticketing/Report Ticketing.xlsx` | Excel workbook | Unknown; operational dataset candidate | 1 | 59,074 data rows | 15 | One row per ticket/intake record | Ticket inquiry / service request | Observed |
| `Report Ticketing/Readme.md` | Markdown | Repository documentation | N/A | N/A | N/A | N/A | QA dataset documentation | Documented |
| `Report Ticketing/Annotation.md` | Markdown | Annotation guidelines | N/A | N/A | N/A | N/A | QA annotation rules | Documented |
| `data/academic_credits_master.csv` | CSV | Synthetic reference data | N/A | Unknown | Unknown | Unknown | Student/academic reference data | Observed, but not primary |
| `data/...` | Mixed synthetic data | Reference/synthetic data | N/A | Unknown | Unknown | Unknown | Synthetic tables | Observed, but not primary |

### What is relevant to the assignment

The actual assignment evidence is concentrated in the Excel workbook. The README and annotation files are not a trustworthy description of the workbook’s schema or operational workflow and therefore must be treated as secondary documentation only.

### File-specific notes

- `Report Ticketing/Report Ticketing.xlsx`:
  - Observed sheet name: `Sheet1`
  - Observed dimension: 59,074 rows, 15 columns
  - Header row is present and populated
  - This is the primary evidence source for the reconnaissance

- `Report Ticketing/Readme.md` and `Annotation.md`:
  - Observed content describes a higher-education QA/annotation system
  - This is not consistent with a ticketing workflow workbook
  - Treat as `Documented` but likely unrelated or stale

---

## 4. Workbook Structure

### Workbook-level facts

| Item | Observed evidence | Assessment |
|---|---|---|
| Workbook file | `Report Ticketing.xlsx` | Primary dataset source |
| Sheets | 1 | Only one sheet present |
| Sheet name | `Sheet1` | Actual sheet verified by workbook inspection |
| Max rows | 59,074 | Includes header row and data rows |
| Max columns | 15 | Full schema observed |

### Sheet-by-sheet description

| Sheet | One row appears to represent | Candidate primary/business key | Important columns | IDs repeat? | Timestamps? | Status/state fields? | Sheet type |
|---|---|---|---|---|---|---|---|
| `Sheet1` | One ticket or inbound inquiry record | `Ticket ID` appears unique; `No` is not a safe primary key | `Ticket ID`, `Ticket Date`, `Ticket Time`, `Ticket Close`, `Kategori`, `Sub Kategori`, `Sub Sub Kategori`, `Ticket SRC`, `Status`, `Agent`, `Remark`, `Referensi`, `Kota`, `Pembelian Form` | `No` repeats; `Ticket ID` does not repeat in observed data | Yes: `Ticket Date`, `Ticket Time`, `Ticket Close` | Yes: `Status` (`closed`, `pending`) | Event/intake ticket table; possible ticket log or CRM-like table |

### Sheet1 schema summary

Observed header row:

- `No`
- `Ticket ID`
- `Ticket Date`
- `Ticket Time`
- `Ticket Close`
- `Kategori`
- `Sub Kategori`
- `Sub Sub Kategori`
- `Ticket SRC`
- `Status`
- `Agent`
- `Remark`
- `Referensi`
- `Kota`
- `Pembelian Form`

### Candidate relationships

- No relationships between sheets are supported because there is only one sheet.
- Candidate relationships within the sheet are limited to:
  - one `Ticket ID` mapped to one record
  - one `Status` value on that record
  - one `Agent` assigned or recorded
  - one `Kategori`/`Sub Kategori`/`Sub Sub Kategori` classification
- These are best treated as candidate structural relationships, not confirmed foreign keys, because there is no separate dimension table, no lookup sheet, and no explicit schema documentation.

---

## 5. Data Grain and Entities

### Observed grain

The workbook appears to be at the grain of one ticket or support inquiry record.

Evidence:
- Each row has a unique `Ticket ID` in observed data
- The row includes creation time, status, classification, source channel, and agent fields
- The table behaves like a record of ticket intake and handling rather than a user or product dimension table

### Candidate entities represented

| Entity | Observed evidence | Assessment |
|---|---|---|
| Ticket / inquiry | `Ticket ID`, `Ticket Date`, `Ticket Time`, `Status`, `Remark` | Strongest candidate entity |
| Ticket category taxonomy | `Kategori`, `Sub Kategori`, `Sub Sub Kategori` | Observed classification hierarchy |
| Channel/source | `Ticket SRC` | Observed channel values |
| Agent/handler | `Agent` | Observed actor field |
| Customer/location | `Kota` | Potential location dimension, but quality issues |
| Reference source | `Referensi` | Possible source/origin field |
| Purchase-form state | `Pembelian Form` | Observed binary field with `BELUM`/`SUDAH` values |

### Date/time fields

Observed:
- `Ticket Date` — present on every row
- `Ticket Time` — present on every row
- `Ticket Close` — present on every row

Operational interpretation:
- `Ticket Date` + `Ticket Time` likely represent creation or first contact time
- `Ticket Close` may represent closure time or a placeholder value when the ticket is still open

### Identifiers

| Column | Observed behavior | Assessment |
|---|---|---|
| `Ticket ID` | Unique across 59,074 rows | Strongest candidate business key |
| `No` | Repeats; appears not unique | Likely a generated row index or sequence label, not a stable key |
| `Agent` | Repeated names | Actor identifier, not a ticket key |

### Categorical / status fields

Observed categories/status fields:
- `Kategori` values: `Pendaftaran Mahasiswa Baru`, `Others`, `Non Pengaduan`
- `Sub Kategori` values: 11 observed categories
- `Sub Sub Kategori` values: 42 observed categories
- `Ticket SRC` values: `WHATSAPP`, `LINE`, `PHONE`, `EMAIL`, `OUTBOUND`
- `Status` values: `closed`, `pending`
- `Pembelian Form` values: `BELUM`, `SUDAH`

### Potentially sensitive fields

- `Remark` contains unstructured free text and may include customer messages or personal details
- `Kota` may be a location attribute but also appears contaminated with non-location values
- `Ticket ID` appears like a generated identifier and may be operationally sensitive

### Relationship to other tables

- No other workbook sheets or linked tables were observed
- No direct foreign-key relationship could be validated
- Candidate internal relationships exist only within a single row and its taxonomy/status columns

---

## 6. Data Quality Findings

### Data quality table

| Issue | Evidence | Why it matters operationally |
|---|---|---|
| Documentation mismatch | README and annotation files describe an Indonesian QA dataset; workbook is ticket-like operational data | The project documentation cannot be trusted as the source-of-truth without validation; risk of wrong business interpretation |
| Single-sheet workbook with no dimension tables | Only one sheet: `Sheet1`; no separate lookup or reference tables | Makes assignment of canonical entities and reliable metrics harder; cannot prove foreign-key integrity |
| `No` is not a safe identifier | `No` has 59,074 rows but only 26,044 unique values; duplicates are common | Row numbers are not unique and therefore cannot be used as a stable ticket identifier |
| `Ticket ID` is likely the real key, but semantics are unclear | `Ticket ID` is unique across observed rows | Good for row-level uniqueness, but unclear whether it is stable across source systems or record-edit cycles |
| `Status` semantics are under-documented and potentially placeholder-driven | Only `closed` and `pending`; 60 rows are pending; 59,014 are closed | This can materially change backlog, closure, and SLA calculations if `pending` is not a real unresolved state |
| `Ticket Close` looks operationally suspicious for pending cases | Pending rows show timestamp placeholders like `2021-01-26 00:00:00` rather than a null or blank | A default value may be used as a close timestamp even when the ticket is still pending, which would distort closure analytics |
| `Kota` is contaminated or inconsistently encoded | Values include `Jakarta`, `jakarta`, `JKT`, `Jakarta Barat`, but also phone-like numeric strings such as `81284558256` and `24330590` | Location analysis is unreliable without a strict validation rule; raw counts might reflect customer phone data rather than city |
| Missingness in important fields | `Sub Sub Kategori`: 18 blanks; `Remark`: 226 blanks; `Referensi`: 34 blanks; `Pembelian Form`: 189 blanks | Missing values can distort trend analysis, segmentation, and rule-driven workflow interpretation |
| Free-text fields are not standardized | `Remark` has 17,201 unique values and appears to contain natural language comments, sometimes with numbers and punctuation | Hard to use as structured workflow data without text standardization or a separate coded taxonomy |
| Category skew | `Pendaftaran Mahasiswa Baru` accounts for nearly all records; other categories are minor | Metrics may appear deceptively stable while being driven by a single category |
| Operational lifecycle is probably incomplete | Only two status states are present; no explicit reopen, escalation, transfer, or SLA breach fields | This is insufficient to model a dependable ticket workflow without additional definitions |
| No evidence of referential integrity across tables | Only one sheet exists; no child tables or master tables observed | Cannot validate linkage between ticket records and supporting entities |

### Important quality issues worth prioritizing

1. `Status` and `Ticket Close` semantics are not proven.
2. `Kota` is not a clean geographic dimension.
3. `No` is not unique and should not be treated as a business key.
4. The workbook is a single flat table, so a trustworthy workflow model requires additional definition.
5. Business interpretation may be distorted by category skew and text contamination.

---

## 7. Initial Workflow Reconstruction

### Observed workflow skeleton

| Stage | Evidence observed | Assessment |
|---|---|---|
| Intake / request creation | `Ticket Date`, `Ticket Time`, `Ticket ID`, `Ticket SRC`, `Remark` | Strongly supported |
| Classification | `Kategori`, `Sub Kategori`, `Sub Sub Kategori` | Strongly supported |
| Source/channel capture | `Ticket SRC` values including `WHATSAPP`, `LINE`, `PHONE`, `EMAIL`, `OUTBOUND` | Strongly supported |
| Agent handling | `Agent` | Observed actor field |
| Outcome/state assignment | `Status` (`closed`, `pending`) | Observed |
| Closure timestamp | `Ticket Close` | Observed, but semantics uncertain |
| Customer context | `Kota`, `Pembelian Form` | Partially observed |

### Hypothesized workflow

The data appears to support a workflow like this:

`Request received / ticket created` -> `Categorized by admission topic` -> `Tracked by source channel` -> `Handled by agent` -> `Status set to pending or closed` -> `Close timestamp recorded`

### What is supported vs. hypothesis

- Supported: ticket creation timestamp, source channel, category taxonomy, agent assignment, status field
- Hypothesis: each row is a customer inquiry or request ticket, not necessarily a work-order or internal task
- Hypothesis: `Ticket Close` marks the end of an operational interaction rather than a formal resolution event
- Hypothesis: `Remark` contains the underlying customer request or agent response, but the raw text is not standardized 
- Needs validation: whether `pending` means unresolved, awaiting customer action, or simply unclosed ticket
- Needs validation: whether `closed` means resolved, completed, or no further action was required

---

## 8. Candidate Business Questions

| Candidate question | Required fields | Availability | Assessment |
|---|---|---|---|
| Which channels generate the most tickets? | `Ticket SRC`, `Ticket Date`, `Ticket ID` | Present | Strong candidate |
| Which categories and subcategories drive ticket load? | `Kategori`, `Sub Kategori`, `Sub Sub Kategori`, `Ticket Date` | Present | Strong candidate |
| Which agents or teams are carrying the most backlog? | `Agent`, `Status`, `Ticket Date`, `Ticket ID` | Present | Plausible but depends on status semantics |
| Where are the tickets concentrated geographically? | `Kota` | Present, but data quality is poor | Candidate only; likely needs validation |
| How long do tickets remain pending or open? | `Ticket Date`, `Ticket Time`, `Ticket Close`, `Status` | Present | Plausible but requires definition of closure semantics |
| Are there recurring issues in specific admission subcategories? | `Sub Kategori`, `Sub Sub Kategori`, `Remark`, `Ticket Date` | Present | Candidate, but free text is noisy |

### Operationally relevant question examples that are supported by available fields

- Which intake source drives the most tickets?
- Which admission topic has the highest ticket volume?
- Which tickets remain unresolved by status?
- Which agent handles the highest volume?

---

## 9. Candidate KPI and Supporting Metrics

### Candidate KPI

| Metric | What it would measure | Required fields | Current data availability | Major assumptions | Major risks |
|---|---|---|---|---|---|
| Ticket backlog rate | Share of tickets still in `pending` or not formally closed | `Status`, `Ticket ID`, `Ticket Date` | Yes | `pending` means unresolved | `pending` may be a placeholder or not a true backlog state |

### Supporting metrics

| Metric | What it would measure | Required fields | Data availability | Assumptions | Risks |
|---|---|---|---|---|---|
| Ticket volume by day/week | Demand trend over time | `Ticket Date`, `Ticket ID` | Yes | Date is creation/reception date | Underlying source chronology may be coarse or incomplete |
| Channel mix | Share of tickets by source channel | `Ticket SRC`, `Ticket ID` | Yes | Channel is a valid operational dimension | Channel may reflect intake medium rather than business origin |
| Category share | Distribution across admission categories | `Kategori`, `Sub Kategori`, `Sub Sub Kategori` | Yes | Taxonomy is stable | Taxonomy may change in meaning over time |
| Pending ticket count | Outstanding unresolved items | `Status`, `Ticket ID` | Yes | `pending` approximates unresolved state | Could be a temporary state or placeholder |
| Cycle time to closure | Time from creation to close | `Ticket Date`, `Ticket Time`, `Ticket Close`, `Status` | Yes, but semantics uncertain | `Ticket Close` is a real closure event | Could represent default values rather than actual closure |

### Important caution

No final KPI should be locked in yet. The current evidence supports the existence of a ticket-like operational table, but not a fully validated business definition of resolution, backlog, or service level.

---

## 10. Data Gaps

| Gap | Why it matters |
|---|---|
| No source-system or business glossary | The definition of a ticket, request, and resolution is unclear |
| No explicit lifecycle specification | Cannot determine what `pending`, `closed`, and `Ticket Close` mean operationally |
| No reliable requester/customer identifier | Cannot distinguish repeat contacts from new tickets |
| No separate master/reference tables | Makes taxonomy validation and dimension control impossible |
| No formal SLA or escalation fields | Prevents dependable service-quality analysis |
| `Kota` appears unreliable | Geographical analytics are not trustworthy without validation |
| `Remark` is unstructured free text | Cannot be reliably used as a defined workflow or outcome field |
| No record of reopens / escalations / transfers | Lifecycle may be incomplete or simplified |
| No evidence of historical coverage beyond date range | Cannot tell if dataset is complete or partial |

---

## 11. FDE Decision Backlog

The next design decisions that will matter later are:

1. What is the canonical business entity: ticket, inquiry, complaint, case, or request?
2. What does `Ticket ID` represent operationally, and is it the true source-system key?
3. What defines a ticket creation event: `Ticket Date` + `Ticket Time`, or something else?
4. What counts as a closed ticket: real resolution, no-action closure, or default-date placeholder?
5. How should `pending` tickets be treated in metrics?
6. How should duplicate-like row-number values (`No`) be handled in the eventual specification?
7. Should `Kota` be treated as geography, as a contaminated field, or as something else entirely?
8. What is the valid grain for the final metric: ticket-level, daily aggregate, category-level, agent-level, or customer-level?
9. What is the valid treatment for free-text `Remark` fields in downstream processing?
10. How should workbook documentation discrepancies be resolved: stale docs, incorrect file naming, or project drift?

---

## 12. Known / Unknown / Assumptions / Hypotheses

| Category | Statement |
|---|---|
| Known | The workbook `Report Ticketing.xlsx` contains exactly one sheet: `Sheet1` |
| Known | The sheet has 59,074 data rows and 15 columns |
| Known | `Ticket ID` is unique across the observed dataset |
| Known | `Status` values are limited to `closed` and `pending` |
| Known | The dataset spans `2020-05-02` through `2022-09-30` |
| Known | The values in `Ticket SRC` are channel-like and appear to be `WHATSAPP`, `LINE`, `PHONE`, `EMAIL`, `OUTBOUND` |
| Known | The README and annotation files are not aligned with the workbook schema |
| Unknown | The exact business meaning of the ticketing process |
| Unknown | Whether the workbook is a source-system extract, a reporting export, or a curated sample |
| Unknown | Whether `Ticket Close` is real closure time or a placeholder |
| Unknown | Whether `Kota` is location data or contaminated data |
| Assumption | One row likely represents one ticket or inquiry record |
| Hypothesis | The table is a ticket intake/handling log rather than a master dimension table |
| Hypothesis | `Remark` contains the customer inquiry or the agent’s response text |
| Needs validation | Whether the dataset is complete and representative for the operational period |

---

## 13. Recommended Next Investigation

1. Validate whether the Excel workbook has hidden metadata or a source-system description outside the README files.
2. Inspect the workbook more deeply for timestamp validity patterns, especially pending rows and closure placeholders.
3. Confirm whether the `Ticket ID` is the business key and whether `No` is a sequence index.
4. Test the cleanliness and reliability of `Kota` through a targeted field audit.
5. Validate the lifecycle meaning of `Status` and `Ticket Close` with minimal sample reviews from closed and pending tickets.
6. Determine whether the project requires a ticket workflow specification before any metric logic is formalized.
7. Decide whether the README/annotation files are irrelevant legacy artifacts or should be treated as authoritative for a separate dataset.

---

## Evidence Summary

### What we know

- The primary project evidence is the workbook `Report Ticketing/Report Ticketing.xlsx`.
- The workbook contains one sheet, `Sheet1`, with 59,074 rows and 15 columns.
- The data appears to have a ticket-like grain: one row per ticket or inquiry record.
- The observed schema includes creation time, close time, category hierarchy, source channel, status, agent, free-text remarks, and location-like field(s).
- The README and annotation files do not describe this workbook and appear to describe a different dataset entirely.

### What we do not know

- The exact business process represented by the ticket data
- Whether `Ticket Close` is a true closure event or a default placeholder
- Whether `Status` is a valid operational state or a simplified reporting flag
- Whether `Kota` is a trustworthy geographic field
- Whether the workbook is complete, sampled, or a partial extract

### What needs validation next

- Confirm the business definition of a ticket and its lifecycle
- Validate `Ticket ID` vs. `No` semantics
- Audit pending vs. closed records for placeholder values
- Validate the location field and category taxonomy quality
- Resolve the mismatch between README/annotation content and workbook reality before writing downstream specs
