from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.config import (
    QUARANTINE_API_ERRORS_OUTPUT,
    VALIDATED_API_OUTPUT,
    VALIDATED_DIRECTORY_OUTPUT,
    VALIDATED_INBOX_OUTPUT,
)
from src.validate import DataValidator


def test_validator_flags_missing_attachments_and_unknown_identity() -> None:
    validator = DataValidator()

    inbox = pd.DataFrame(
        [
            {
                "Message_ID": "MSG-1",
                "Timestamp_IST": "2026-09-20 02:15:00",
                "Sender_Email": "student.unknown@gmail.com",
                "Subject": "Test",
                "Body": "Please see the attached document for the receipt and invoice.",
                "CC": "",
                "BCC": "",
                "Has_Attachment": False,
            },
            {
                "Message_ID": "MSG-2",
                "Timestamp_IST": "2026-09-20 03:20:00",
                "Sender_Email": "known.student@university.edu",
                "Subject": "Test 2",
                "Body": "No attachment needed.",
                "CC": "",
                "BCC": "",
                "Has_Attachment": True,
            },
        ]
    )
    directory = pd.DataFrame(
        [{"student_id": "24bcs10001", "official_email": "known.student@university.edu"}]
    )

    normalized = validator.normalize_timestamps(inbox)
    resolved = validator.resolve_identities(normalized, directory)
    flagged = validator.flag_attachment_anomalies(resolved)

    assert bool(flagged.loc[0, "Missing_Attachment_Anomaly"]) is True
    assert flagged.loc[0, "student_id"] == "Unknown Identity"
    assert flagged.loc[1, "student_id"] == "24bcs10001"
    assert bool(flagged.loc[0, "Is_Off_Hours"]) is True


def test_validator_standardizes_datetime_and_splits_api_errors() -> None:
    validator = DataValidator()
    payload = [
        {"error": "500 Internal Server Error"},
        {"error": "504 Gateway Timeout"},
        {"interaction_id": "abc", "student_id": "24bcs10001", "reason": "ok"},
        {"interaction_id": "abc", "student_id": "24bcs10001", "reason": "ok"},
    ]

    valid_records, error_records, stats = validator.validate_api_records(payload)
    assert len(valid_records) == 1
    assert len(error_records) == 2
    assert stats["valid_api_records"] == 1
    assert stats["api_error_records"] == 2

    inbox = pd.DataFrame([
        {"Message_ID": "MSG-1", "Timestamp_IST": "2026-09-20 08:00:00", "Body": "text", "Has_Attachment": False},
        {"Message_ID": "MSG-1", "Timestamp_IST": "2026-09-20 08:00:00", "Body": "text", "Has_Attachment": False},
        {"Message_ID": "MSG-2", "Timestamp_IST": "2026-09-20 03:00:00", "Body": "text", "Has_Attachment": True},
    ])
    validated_inbox, duplicate_rows, _ = validator.validate_inbox(inbox)
    normalized = validator.normalize_timestamps(validated_inbox)
    assert len(duplicate_rows) == 1
    assert normalized["Timestamp_IST"].iloc[0].endswith("08:00:00")
    assert bool(normalized["Is_Off_Hours"].iloc[1]) is True


def test_validate_inbox_catches_dup_suffixed_retry_captures() -> None:
    """Regression test: the inbox simulator marks a duplicate mailbox
    ingestion capture by appending a retry suffix ("-dup1", "-dup2", ...) to
    the ORIGINAL Message_ID and extra quoting to the Body, so a dedup key
    that includes the exact Message_ID/Body (the previous implementation)
    never matches these rows against their original. That silently let 993
    of ~34k injected duplicate rows (see findings/02_inbox_simulation_spec.md)
    straight through validation with zero rows quarantined.
    """
    validator = DataValidator()
    inbox = pd.DataFrame(
        [
            {"Message_ID": "MSG-TICKET-1", "Timestamp_IST": "2026-09-20 08:00:00", "Body": "Original body.", "Has_Attachment": False},
            {
                "Message_ID": "MSG-TICKET-1-dup3",
                "Timestamp_IST": "2026-09-20 08:00:00",
                "Body": "Original body.\n\n[duplicate intake row captured again in mailbox ingestion]",
                "Has_Attachment": False,
            },
            {"Message_ID": "MSG-TICKET-2", "Timestamp_IST": "2026-09-21 09:00:00", "Body": "Different issue entirely.", "Has_Attachment": False},
        ]
    )

    validated, duplicate_rows, stats = validator.validate_inbox(inbox)

    assert stats["duplicate_inbox_rows"] == 1
    assert len(validated) == 2
    assert duplicate_rows[0]["Message_ID"] == "MSG-TICKET-1-dup3"


def test_quarantine_critical_nulls_does_not_swallow_api_error_envelopes() -> None:
    """Regression test: HTTP error envelopes ({"error": "500 ..."}) never
    carry an interaction_id, so the critical-null check used to classify
    them as "missing interaction_id" and remove them before
    validate_api_records() ever saw them - meaning data/quarantine/
    api_errors.json was always empty on real data, and the audit trail
    recorded the wrong reason (critical null instead of upstream API error)
    for every one of them.
    """
    validator = DataValidator()
    inbox = pd.DataFrame([{"Message_ID": "MSG-1", "Sender_Email": "a@b.edu", "Timestamp_IST": "2026-09-20 08:00:00"}])
    directory = pd.DataFrame([{"student_id": "24bcs10001"}])
    api_payload = [
        {"error": "500 Internal Server Error"},
        {"error": "504 Gateway Timeout"},
        {"interaction_id": None, "student_id": "24bcs10001"},  # a genuine critical null
        {"interaction_id": "abc", "student_id": "24bcs10001"},
    ]

    _, _, cleaned_api_payload, critical_rows, critical_count = validator.quarantine_critical_nulls(
        inbox, directory, api_payload
    )

    assert critical_count == 1
    assert critical_rows[0]["missing_fields"] == ["interaction_id"]
    assert json.loads(critical_rows[0]["raw_record"]).get("interaction_id") is None

    valid_records, error_records, api_stats = validator.validate_api_records(cleaned_api_payload)
    assert api_stats["api_error_records"] == 2
    assert api_stats["valid_api_records"] == 1
    assert {r["error"] for r in error_records} == {"500 Internal Server Error", "504 Gateway Timeout"}


def test_validate_resolution_events_joins_all_three_sources_and_quarantines_unmatched_rows() -> None:
    validator = DataValidator()
    directory = pd.DataFrame(
        [{"student_id": "24bcs10001", "enrollment_number": "ENR-2024001"}]
    )
    mess_roster = pd.DataFrame(
        [{"student_id": "24bcs10001", "resolution_timestamp": "2026-08-01 00:00:00", "state": "Cleared"}]
    )
    finance_disputes = pd.DataFrame(
        [
            {"enrollment_number": "ENR-2024001", "resolved_date_ist": "2026-08-02 00:00:00", "status": "Closed"},
            {"enrollment_number": "ENR-DOES-NOT-EXIST", "resolved_date_ist": "2026-08-03 00:00:00", "status": "Closed"},
        ]
    )
    academic_credits = pd.DataFrame(
        [{"univ_id": "24bcs10001", "action_date": "2026-08-04 00:00:00", "outcome": "Done"}]
    )

    combined, quarantined, stats = validator.validate_resolution_events(
        directory, mess_roster, finance_disputes, academic_credits
    )

    assert stats["resolution_events"] == 3
    assert set(combined["student_id"]) == {"24bcs10001"}
    assert set(combined["source_system"]) == {"mess_roster", "finance_disputes", "academic_credits"}
    # The finance row with an enrollment_number absent from the directory
    # cannot be resolved to a student_id and must be quarantined, not dropped
    # silently or attributed to the wrong student.
    assert stats["quarantined_resolution_events"] == 1
    assert quarantined[0]["source_system"] == "finance_disputes"


def test_validator_generates_validated_outputs() -> None:
    validator = DataValidator()
    summary = validator.run_validation()

    assert Path(VALIDATED_API_OUTPUT).exists()
    assert Path(VALIDATED_DIRECTORY_OUTPUT).exists()
    assert Path(VALIDATED_INBOX_OUTPUT).exists()
    assert Path(QUARANTINE_API_ERRORS_OUTPUT).exists()

    validated_api = json.loads(Path(VALIDATED_API_OUTPUT).read_text(encoding="utf-8"))
    assert isinstance(validated_api, list)
    assert "validated_inbox_path" in summary
    assert "validated_directory_path" in summary
