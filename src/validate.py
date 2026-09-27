from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import (
    API_INTERACTIONS_INPUT,
    QUARANTINE_API_ERRORS_OUTPUT,
    QUARANTINE_CRITICAL_NULLS_OUTPUT,
    QUARANTINE_DIRECTORY_OUTPUT,
    QUARANTINE_INBOX_OUTPUT,
    QUARANTINE_RESOLUTION_EVENTS_OUTPUT,
    RAW_ACADEMIC_CREDITS_OUTPUT,
    RAW_API_OUTPUT,
    RAW_DIRECTORY_OUTPUT,
    RAW_FINANCE_DISPUTES_OUTPUT,
    RAW_INBOX_INPUT,
    RAW_INBOX_OUTPUT,
    RAW_MESS_ROSTER_OUTPUT,
    STUDENT_DIRECTORY_INPUT,
    VALIDATED_API_OUTPUT,
    VALIDATED_DIRECTORY_OUTPUT,
    VALIDATED_INBOX_OUTPUT,
    VALIDATED_RESOLUTION_EVENTS_OUTPUT,
    ensure_configured_source_files,
    ensure_quarantine_dir,
    ensure_raw_dir,
    ensure_validated_dir,
)
from src.extract import extract_all

# Message_ID suffix appended by the inbox simulator to mark a duplicate
# mailbox-ingestion capture of an already-seen message (see
# generate_raw_student_alert_inbox.py::inject_communication_anomalies).
_DUPLICATE_MESSAGE_ID_SUFFIX = re.compile(r"-dup\d+$")

_API_ERROR_VALUES = {"500 Internal Server Error", "504 Gateway Timeout", "504 Gateway Timeout/Timeout"}


class DataValidator:
    def __init__(self) -> None:
        self.raw_inbox_path = Path(RAW_INBOX_INPUT)
        self.directory_path = Path(STUDENT_DIRECTORY_INPUT)
        self.api_path = Path(API_INTERACTIONS_INPUT)

    def _load_raw_inputs(self) -> tuple[pd.DataFrame, pd.DataFrame, list[Any], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        ensure_configured_source_files()
        extract_all()
        ensure_raw_dir()
        ensure_validated_dir()
        ensure_quarantine_dir()

        inbox_df = pd.read_csv(RAW_INBOX_OUTPUT)
        directory_df = pd.read_csv(RAW_DIRECTORY_OUTPUT)
        with Path(RAW_API_OUTPUT).open("r", encoding="utf-8") as handle:
            api_payload = json.load(handle)
        mess_roster_df = pd.read_csv(RAW_MESS_ROSTER_OUTPUT)
        finance_disputes_df = pd.read_csv(RAW_FINANCE_DISPUTES_OUTPUT)
        academic_credits_df = pd.read_csv(RAW_ACADEMIC_CREDITS_OUTPUT)
        return inbox_df, directory_df, api_payload, mess_roster_df, finance_disputes_df, academic_credits_df

    @staticmethod
    def _is_critical_missing(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        try:
            return pd.isna(value)
        except TypeError:
            return False

    def quarantine_critical_nulls(
        self,
        inbox_df: pd.DataFrame,
        directory_df: pd.DataFrame,
        api_payload: list[Any],
    ) -> tuple[pd.DataFrame, pd.DataFrame, list[Any], list[dict[str, Any]], int]:
        critical_rows: list[dict[str, Any]] = []

        inbox_mask = inbox_df[["Message_ID", "Sender_Email", "Timestamp_IST"]].isnull().any(axis=1)
        inbox_null_rows = inbox_df.loc[inbox_mask].copy()
        critical_rows.extend(
            {
                "source": "inbox",
                "row_index": int(index),
                "missing_fields": [field for field in ["Message_ID", "Sender_Email", "Timestamp_IST"] if self._is_critical_missing(row.get(field))],
                "raw_record": json.dumps(row.to_dict(), ensure_ascii=False),
            }
            for index, row in inbox_null_rows.iterrows()
        )
        inbox_df = inbox_df.loc[~inbox_mask].copy()

        directory_mask = directory_df["student_id"].isnull() | directory_df["student_id"].astype(str).str.strip().eq("")
        directory_null_rows = directory_df.loc[directory_mask].copy()
        critical_rows.extend(
            {
                "source": "directory",
                "row_index": int(index),
                "missing_fields": ["student_id"],
                "raw_record": json.dumps(row.to_dict(), ensure_ascii=False),
            }
            for index, row in directory_null_rows.iterrows()
        )
        directory_df = directory_df.loc[~directory_mask].copy()

        cleaned_api_payload: list[Any] = []
        for idx, item in enumerate(api_payload):
            if not isinstance(item, dict):
                cleaned_api_payload.append(item)
                continue
            # HTTP error envelopes (e.g. {"error": "500 Internal Server Error"})
            # never carry an interaction_id by design. They are a distinct
            # anomaly (an upstream API failure) from a malformed/incomplete
            # record, so they must be left for validate_api_records() to
            # triage into quarantine/api_errors.json with the real reason,
            # instead of being absorbed here as a generic "critical null".
            if "error" in item:
                cleaned_api_payload.append(item)
                continue
            if item.get("interaction_id") is None or self._is_critical_missing(item.get("interaction_id")):
                critical_rows.append(
                    {
                        "source": "api",
                        "row_index": idx,
                        "missing_fields": ["interaction_id"],
                        "raw_record": json.dumps(item, ensure_ascii=False),
                    }
                )
                continue
            cleaned_api_payload.append(item)

        if critical_rows:
            quarantine_df = pd.DataFrame(critical_rows)
            quarantine_df.to_csv(QUARANTINE_CRITICAL_NULLS_OUTPUT, index=False)
            print(f"[critical_null_check] quarantined {len(critical_rows)} rows missing required fields")
        else:
            pd.DataFrame(columns=["source", "row_index", "missing_fields", "raw_record"]).to_csv(
                QUARANTINE_CRITICAL_NULLS_OUTPUT,
                index=False,
            )
            print("[critical_null_check] quarantined 0 rows missing required fields")

        return inbox_df, directory_df, cleaned_api_payload, critical_rows, len(critical_rows)

    def validate_api_records(self, api_payload: list[Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
        valid_records: list[dict[str, Any]] = []
        error_records: list[dict[str, Any]] = []
        for item in api_payload:
            if not isinstance(item, dict):
                valid_records.append({"raw_record": item})
                continue
            error_value = item.get("error")
            if error_value and (
                error_value in _API_ERROR_VALUES
                or "500" in str(error_value)
                or "504" in str(error_value)
            ):
                error_records.append(item)
                continue
            valid_records.append(item)

        deduped_valid: list[dict[str, Any]] = []
        seen: set[str] = set()
        for record in valid_records:
            key = json.dumps(record, sort_keys=True, ensure_ascii=False)
            if key in seen:
                continue
            seen.add(key)
            deduped_valid.append(record)

        stats = {
            "valid_api_records": len(deduped_valid),
            "api_error_records": len(error_records),
            "deduplicated_api_retries": len(valid_records) - len(deduped_valid),
        }
        return deduped_valid, error_records, stats

    def validate_directory(self, directory_df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, int]]:
        duplicate_mask = directory_df.duplicated(subset=["student_id"], keep="first")
        duplicates = directory_df.loc[duplicate_mask].copy()
        validated = directory_df.loc[~duplicate_mask].copy()

        duplicate_rows = duplicates.to_dict(orient="records")
        stats = {
            "directory_rows": len(directory_df),
            "validated_directory_rows": len(validated),
            "duplicate_directory_rows": len(duplicate_rows),
        }
        return validated, duplicate_rows, stats

    def validate_inbox(self, inbox_df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, int]]:
        # Repeat mailbox-ingestion captures of the same message keep the same
        # Message-ID root and Timestamp_IST, but the simulator (and real mail
        # relays) may append a retry suffix ("-dup1", "-dup2", ...) to the
        # Message-ID and extra quoting to the Body on each re-delivery. Keying
        # only on the exact Message_ID/Body therefore misses every such
        # duplicate; normalize the Message-ID root first.
        message_root = (
            inbox_df["Message_ID"].astype(str).str.replace(_DUPLICATE_MESSAGE_ID_SUFFIX, "", regex=True)
        )
        duplicate_keys = pd.DataFrame(
            {"root": message_root, "Timestamp_IST": inbox_df["Timestamp_IST"]}
        ).duplicated(keep="first")
        duplicate_rows = inbox_df.loc[duplicate_keys].copy()
        validated = inbox_df.loc[~duplicate_keys].copy()

        stats = {
            "inbox_rows": len(inbox_df),
            "validated_inbox_rows": len(validated),
            "duplicate_inbox_rows": len(duplicate_rows),
        }
        return validated, duplicate_rows.to_dict(orient="records"), stats

    def normalize_timestamps(self, inbox_df: pd.DataFrame) -> pd.DataFrame:
        output = inbox_df.copy()
        output["Timestamp_IST"] = pd.to_datetime(output["Timestamp_IST"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
        output["Is_Batch_Spike"] = output.groupby("Timestamp_IST")["Timestamp_IST"].transform("size") > 50
        output["Is_Off_Hours"] = output["Timestamp_IST"].dt.hour.between(2, 5, inclusive="both")
        output["Timestamp_IST"] = output["Timestamp_IST"].dt.strftime("%Y-%m-%d %H:%M:%S")
        return output

    def resolve_identities(self, inbox_df: pd.DataFrame, directory_df: pd.DataFrame) -> pd.DataFrame:
        resolved = inbox_df.copy()
        sender_lookup = directory_df.set_index("official_email")["student_id"].to_dict()
        resolved["student_id"] = resolved["Sender_Email"].map(sender_lookup).fillna("Unknown Identity")
        return resolved

    def flag_attachment_anomalies(self, inbox_df: pd.DataFrame) -> pd.DataFrame:
        output = inbox_df.copy()
        body_text = output["Body"].fillna("").astype(str).str.lower()
        output["Missing_Attachment_Anomaly"] = (
            body_text.str.contains(r"attach|receipt|document", case=False, na=False)
            & output["Has_Attachment"].fillna(False).astype(bool).eq(False)
        )
        return output

    def validate_resolution_events(
        self,
        directory_df: pd.DataFrame,
        mess_roster_df: pd.DataFrame,
        finance_disputes_df: pd.DataFrame,
        academic_credits_df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, int]]:
        """Normalize the three resolution-signal sources into one
        (student_id, resolution_timestamp, resolution_state, source_system)
        table so the modeling stage can determine whether a request was ever
        actually closed out downstream, instead of assuming none ever were.
        """
        enrollment_to_student = directory_df.set_index("enrollment_number")["student_id"].to_dict()
        quarantined: list[dict[str, Any]] = []
        frames: list[pd.DataFrame] = []

        mess = mess_roster_df.copy()
        mess_missing = mess["student_id"].isnull() | mess["student_id"].astype(str).str.strip().eq("")
        quarantined.extend(
            {"source_system": "mess_roster", "row_index": int(i), "raw_record": json.dumps(row.to_dict(), ensure_ascii=False)}
            for i, row in mess.loc[mess_missing].iterrows()
        )
        mess = mess.loc[~mess_missing].copy()
        frames.append(
            pd.DataFrame(
                {
                    "student_id": mess["student_id"],
                    "resolution_timestamp": pd.to_datetime(mess["resolution_timestamp"], errors="coerce"),
                    "resolution_state": mess["state"],
                    "source_system": "mess_roster",
                }
            )
        )

        finance = finance_disputes_df.copy()
        finance["student_id"] = finance["enrollment_number"].map(enrollment_to_student)
        finance_missing = finance["student_id"].isnull()
        quarantined.extend(
            {"source_system": "finance_disputes", "row_index": int(i), "raw_record": json.dumps(row.to_dict(), ensure_ascii=False)}
            for i, row in finance.loc[finance_missing].iterrows()
        )
        finance = finance.loc[~finance_missing].copy()
        frames.append(
            pd.DataFrame(
                {
                    "student_id": finance["student_id"],
                    "resolution_timestamp": pd.to_datetime(finance["resolved_date_ist"], errors="coerce"),
                    "resolution_state": finance["status"],
                    "source_system": "finance_disputes",
                }
            )
        )

        academic = academic_credits_df.copy()
        academic_missing = academic["univ_id"].isnull() | academic["univ_id"].astype(str).str.strip().eq("")
        quarantined.extend(
            {"source_system": "academic_credits", "row_index": int(i), "raw_record": json.dumps(row.to_dict(), ensure_ascii=False)}
            for i, row in academic.loc[academic_missing].iterrows()
        )
        academic = academic.loc[~academic_missing].copy()
        frames.append(
            pd.DataFrame(
                {
                    "student_id": academic["univ_id"],
                    "resolution_timestamp": pd.to_datetime(academic["action_date"], errors="coerce"),
                    "resolution_state": academic["outcome"],
                    "source_system": "academic_credits",
                }
            )
        )

        combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
            columns=["student_id", "resolution_timestamp", "resolution_state", "source_system"]
        )
        combined = combined.dropna(subset=["resolution_timestamp"]).sort_values("resolution_timestamp").reset_index(drop=True)

        stats = {
            "resolution_events": len(combined),
            "quarantined_resolution_events": len(quarantined),
            "mess_roster_events": int((combined["source_system"] == "mess_roster").sum()) if not combined.empty else 0,
            "finance_disputes_events": int((combined["source_system"] == "finance_disputes").sum()) if not combined.empty else 0,
            "academic_credits_events": int((combined["source_system"] == "academic_credits").sum()) if not combined.empty else 0,
        }
        return combined, quarantined, stats

    def run_validation(self) -> dict[str, Any]:
        (
            inbox_df,
            directory_df,
            api_payload,
            mess_roster_df,
            finance_disputes_df,
            academic_credits_df,
        ) = self._load_raw_inputs()

        inbox_df, directory_df, api_payload, critical_null_rows, critical_null_count = self.quarantine_critical_nulls(
            inbox_df,
            directory_df,
            api_payload,
        )

        valid_api, api_errors, api_stats = self.validate_api_records(api_payload)
        validated_directory, duplicate_directory_rows, directory_stats = self.validate_directory(directory_df)
        validated_inbox, duplicate_inbox_rows, inbox_stats = self.validate_inbox(inbox_df)
        validated_resolution_events, quarantined_resolution_events, resolution_stats = self.validate_resolution_events(
            validated_directory,
            mess_roster_df,
            finance_disputes_df,
            academic_credits_df,
        )

        validated_inbox = self.normalize_timestamps(validated_inbox)
        validated_inbox = self.resolve_identities(validated_inbox, validated_directory)
        validated_inbox = self.flag_attachment_anomalies(validated_inbox)

        Path(VALIDATED_API_OUTPUT).parent.mkdir(parents=True, exist_ok=True)
        with Path(VALIDATED_API_OUTPUT).open("w", encoding="utf-8") as handle:
            json.dump(valid_api, handle, ensure_ascii=False, indent=2)

        validated_directory.to_csv(VALIDATED_DIRECTORY_OUTPUT, index=False)
        validated_inbox.to_csv(VALIDATED_INBOX_OUTPUT, index=False)
        validated_resolution_events.to_csv(VALIDATED_RESOLUTION_EVENTS_OUTPUT, index=False)

        if quarantined_resolution_events:
            pd.DataFrame(quarantined_resolution_events).to_csv(QUARANTINE_RESOLUTION_EVENTS_OUTPUT, index=False)
        else:
            pd.DataFrame(columns=["source_system", "row_index", "raw_record"]).to_csv(
                QUARANTINE_RESOLUTION_EVENTS_OUTPUT, index=False
            )

        with Path(QUARANTINE_API_ERRORS_OUTPUT).open("w", encoding="utf-8") as handle:
            json.dump(api_errors, handle, ensure_ascii=False, indent=2)
        with Path(QUARANTINE_DIRECTORY_OUTPUT).open("w", encoding="utf-8") as handle:
            json.dump(duplicate_directory_rows, handle, ensure_ascii=False, indent=2)
        with Path(QUARANTINE_INBOX_OUTPUT).open("w", encoding="utf-8") as handle:
            json.dump(duplicate_inbox_rows, handle, ensure_ascii=False, indent=2)

        summary = {
            "api": api_stats,
            "directory": directory_stats,
            "inbox": inbox_stats,
            "resolution_events": resolution_stats,
            "critical_null_rows": critical_null_count,
            "critical_nulls_path": str(QUARANTINE_CRITICAL_NULLS_OUTPUT),
            "validated_api_path": str(VALIDATED_API_OUTPUT),
            "validated_directory_path": str(VALIDATED_DIRECTORY_OUTPUT),
            "validated_inbox_path": str(VALIDATED_INBOX_OUTPUT),
            "validated_resolution_events_path": str(VALIDATED_RESOLUTION_EVENTS_OUTPUT),
        }
        return summary


def validate_all() -> dict[str, Any]:
    validator = DataValidator()
    return validator.run_validation()


if __name__ == "__main__":
    print(validate_all())
