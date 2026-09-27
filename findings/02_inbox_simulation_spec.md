# 02. Inbox simulation specification

## Objective
This transformation converts a cleaned operational ticketing dataset into a raw, noisy student inbox dataset for data-engineering anomaly testing. The pipeline reads source records from the workbook and the official student directory, then maps each record to an email-like message while intentionally introducing identity, communication, workflow, formatting, and temporal anomalies.

## Input sources
- Student directory: `data/student_directory_master.csv`
- Ticket dataset: `Report Ticketing/Report Ticketing.xlsx`
- Output: `data/raw_student_alert_inbox.csv`

## Transformation logic
1. Read the directory and keep only valid `official_email` rows.
2. Read the ticket workbook and keep rows whose `Ticket SRC` is `EMAIL` or `WHATSAPP`.
3. Parse `Ticket Date` and `Ticket Time` into a single timestamp column, then normalize to the `IST`-style local time convention used in the ticketing source.
4. Translate the Indonesian `Remark` field into English using a translation dictionary with a Google fallback.
5. Generate an email subject from the category and the translated issue text.
6. Assign each message to a sender by hashing the `Ticket ID` to a stable student record in the directory.
7. Replace 15% of sender addresses with synthetic Gmail identities; 5% of these personal emails are intentionally left unmapped to the university directory.
8. Inject communication noise, duplicate mail ingestion rows, urgent black-hole requests, malformed fee amounts, and timezone drift before writing the final CSV.
9. Right-censor the final dataset by trimming the last 2 days of records so the inbox resembles a partial historical collection.

## Output schema
| Column | Type | Meaning |
|---|---|---|
| `Message_ID` | string | Stable identifier for each inbox message |
| `Timestamp_IST` | string | Event time in the output inbox stream, with timezone anomalies intentionally introduced for a small subset |
| `Sender_Email` | string | Official university address or synthetic Gmail address |
| `Subject` | string | Email subject generated from issue class and body text |
| `Body` | string | English-rendered, noisy inbox content, including simulated thread and workflow artifacts |
| `CC` | string | Empty string placeholder for mailbox-style metadata |
| `BCC` | string | Empty string placeholder for mailbox-style metadata |
| `Has_Attachment` | bool | Boolean flag that is deliberately inconsistent in some workflow anomalies |

## Injected anomaly distribution
| Anomaly family | Injection rule | Target distribution |
|---|---|---|
| Identity drift | Replace official student addresses with synthetic `first.last99@gmail.com` format | 15% of rows |
| Unmapped Gmail identities | Leave a subset of the synthetic Gmail identities detached from the directory | 5% of personal identities |
| Communication noise | Append disclaimers, mobile-signature text, and broken thread markers | 18% of rows |
| Broken conversation threads | Alter subject prefixes or thread semantics for the same issue | 8% of rows |
| Duplicate ingestion rows | Repeat a subset of rows as duplicate inbox captures | 3% of rows |
| Workflow contradictions | Add references to documents/receipts when `Has_Attachment` is false | 12% of rows |
| Black-hole requests | Add urgent language with no tracking or case reference | 5% of rows |
| Fee formatting anomalies | Inject malformed or mixed-format monetary strings in fee or mess disputes | ~50% of fee-related rows |
| Timezone drift | Shift a subset of timestamps by +5 hours to simulate UTC mislabeling | 5% of rows |
| Right-censoring | Remove the last 2 days of ticket traffic to simulate partial ingestion | Applied once to the final extracted set |

## Resulting dataset summary
- Rows written: 34126
- Personal-email substitutions: 5136
- Unmapped synthetic Gmail records: 5136
- Rows with `Has_Attachment = False`: 34126
- Rows with noisy communication text: 2813
- Duplicate ingestion rows: 993
- Urgent / black-hole requests: 1708
- Fee-malformed rows: 3108

## Notes
The transformation is intentionally designed to be realistic but noisy. It preserves a strong identity-to-record mapping for most rows while introducing a controlled share of conflicting metadata, broken threads, duplicate ingestion, and queue black holes to support downstream analytics and anomaly-detection exercises.
