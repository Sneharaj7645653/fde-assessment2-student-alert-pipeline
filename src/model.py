from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import (
    MODELED_KPI_OUTPUT,
    MODELED_REQUESTS_OUTPUT,
    VALIDATED_API_OUTPUT,
    VALIDATED_DIRECTORY_OUTPUT,
    VALIDATED_INBOX_OUTPUT,
    VALIDATED_RESOLUTION_EVENTS_OUTPUT,
    ensure_validated_dir,
)


class WorkflowModeler:
    def __init__(self) -> None:
        self.inbox_path = Path(VALIDATED_INBOX_OUTPUT)
        self.directory_path = Path(VALIDATED_DIRECTORY_OUTPUT)
        self.api_path = Path(VALIDATED_API_OUTPUT)
        self.resolution_events_path = Path(VALIDATED_RESOLUTION_EVENTS_OUTPUT)

    def load_validated_data(self) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]], pd.DataFrame]:
        inbox_df = pd.read_csv(self.inbox_path)
        directory_df = pd.read_csv(self.directory_path)
        with self.api_path.open("r", encoding="utf-8") as handle:
            api_payload = json.load(handle)
        if self.resolution_events_path.exists():
            resolution_events_df = pd.read_csv(self.resolution_events_path, parse_dates=["resolution_timestamp"])
        else:
            resolution_events_df = pd.DataFrame(columns=["student_id", "resolution_timestamp", "resolution_state", "source_system"])
        return inbox_df, directory_df, api_payload, resolution_events_df

    def build_request_threads(self, inbox_df: pd.DataFrame) -> pd.DataFrame:
        output = inbox_df.copy()
        if output.empty:
            output["Request_ID"] = pd.Series(dtype="str")
            output["Request_Group_Sequence"] = pd.Series(dtype="int")
            return output

        output = output.sort_values(["Sender_Email", "Timestamp_IST"]).copy()
        output["Timestamp_IST"] = pd.to_datetime(output["Timestamp_IST"], errors="coerce")

        request_ids: list[str] = []
        current_request = 0
        previous_sender: str | None = None
        previous_time: pd.Timestamp | None = None

        for _, row in output.iterrows():
            sender = str(row["Sender_Email"]) if pd.notna(row["Sender_Email"]) else ""
            timestamp = row["Timestamp_IST"]

            if pd.isna(timestamp):
                request_ids.append(f"REQ-{current_request}")
                continue

            if sender != previous_sender or previous_time is None or (timestamp - previous_time) > pd.Timedelta(hours=48):
                current_request += 1
            request_ids.append(f"REQ-{current_request}")
            previous_sender = sender
            previous_time = timestamp

        output["Request_ID"] = request_ids
        output["Request_Group_Sequence"] = 1
        return output

    def parse_body_features(self, inbox_df: pd.DataFrame) -> pd.DataFrame:
        output = inbox_df.copy()
        body_series = output["Body"].fillna("").astype(str)

        output["Invisible_Handoff"] = body_series.str.contains(r"\bFWD:\b|\bFW:\b|\bFORWARDED\b", case=False, na=False)
        output["Financial_Amount"] = body_series.apply(self._extract_financial_amount)
        return output

    @staticmethod
    def _extract_financial_amount(text: str) -> str | None:
        if not text:
            return None
        patterns = [
            r"Rs\.?\s*[,\d]+(?:\s*[,\.]\s*\d+)?",
            r"₹\s*[,\d]+(?:\s*[,\.]\s*\d+)?",
            r"\b\d{1,3}(?:\s\d{3})+(?:\.\d{2})?\b",
            r"\b\d+(?:\s\d+)+(?:\.\d+)?\b",
            r"\b\d+(?:,\d{3})+(?:\.\d+)?\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return None

    def resolve_request_timestamps(self, modeled_df: pd.DataFrame, resolution_events: pd.DataFrame) -> pd.DataFrame:
        """Attach a Resolution_Timestamp to each request thread by matching it
        against the mess-roster, finance-dispute, and academic-credit
        resolution events (see src/validate.py::validate_resolution_events).

        These events are keyed only by student_id, not by request, so a
        student with several requests needs a rule for which event closes
        which request. We anchor each request to its first message
        (Submission_Timestamp) and, per student, greedily assign the
        earliest not-yet-claimed resolution event whose timestamp is at or
        after that submission time. This is the key FDE judgement call in
        the modeling stage: it prevents one resolution event from being
        double-counted across multiple requests, and it never assigns a
        resolution that could not causally follow the request. A request
        with no matching event downstream is left unresolved rather than
        guessed at (see calculate_kpi / Black-Hole handling).
        """
        output = modeled_df.copy()
        if output.empty:
            output["Resolution_Timestamp"] = pd.NaT
            output["Resolution_Source"] = pd.Series(dtype="object")
            output["Time_Travel_Anomaly"] = False
            output["Censoring_Status"] = "Resolved"
            return output

        submissions = (
            output.groupby("Request_ID")
            .agg(student_id=("student_id", "first"), Submission_Timestamp=("Timestamp_IST", "min"))
            .reset_index()
        )
        submissions["Submission_Timestamp"] = pd.to_datetime(submissions["Submission_Timestamp"], errors="coerce")

        assignments = self._match_resolution_events(submissions, resolution_events)

        output = output.merge(assignments, on="Request_ID", how="left")
        output["Time_Travel_Anomaly"] = False
        output["Censoring_Status"] = "Resolved"
        return output

    @staticmethod
    def _match_resolution_events(submissions: pd.DataFrame, resolution_events: pd.DataFrame) -> pd.DataFrame:
        events_by_student: dict[Any, list[dict[str, Any]]] = {}
        if resolution_events is not None and not resolution_events.empty:
            events = resolution_events.copy()
            events["resolution_timestamp"] = pd.to_datetime(events["resolution_timestamp"], errors="coerce")
            events = events.dropna(subset=["resolution_timestamp"]).sort_values("resolution_timestamp")
            for student_id, group in events.groupby("student_id"):
                events_by_student[student_id] = group[["resolution_timestamp", "source_system"]].to_dict("records")

        rows: list[dict[str, Any]] = []
        for student_id, group in submissions.groupby("student_id", sort=False):
            candidate_events = list(events_by_student.get(student_id, []))
            cursor = 0
            for _, request in group.sort_values("Submission_Timestamp").iterrows():
                submission_time = request["Submission_Timestamp"]
                resolution_timestamp = pd.NaT
                resolution_source = None
                if pd.notna(submission_time):
                    while cursor < len(candidate_events) and candidate_events[cursor]["resolution_timestamp"] < submission_time:
                        cursor += 1
                    if cursor < len(candidate_events):
                        resolution_timestamp = candidate_events[cursor]["resolution_timestamp"]
                        resolution_source = candidate_events[cursor]["source_system"]
                        cursor += 1
                rows.append(
                    {
                        "Request_ID": request["Request_ID"],
                        "Resolution_Timestamp": resolution_timestamp,
                        "Resolution_Source": resolution_source,
                    }
                )
        return pd.DataFrame(rows, columns=["Request_ID", "Resolution_Timestamp", "Resolution_Source"])

    def build_request_summary(self, modeled_df: pd.DataFrame, api_payload: list[dict[str, Any]]) -> pd.DataFrame:
        api_df = pd.DataFrame(api_payload)
        if not api_df.empty and "timestamp_ist" in api_df.columns:
            api_df["timestamp_ist"] = pd.to_datetime(api_df["timestamp_ist"], errors="coerce")

        grouped: list[dict[str, Any]] = []
        for _, request_group in modeled_df.groupby("Request_ID", sort=False):
            request_group = request_group.sort_values("Timestamp_IST")
            first_time = pd.to_datetime(request_group["Timestamp_IST"].min(), errors="coerce")
            student_id = request_group["student_id"].dropna().iloc[0] if "student_id" in request_group.columns else None
            has_invisible_handoff = bool(request_group["Invisible_Handoff"].any())
            has_financial_amount = bool(request_group["Financial_Amount"].notna().any())

            resolution_time = request_group["Resolution_Timestamp"].dropna()
            resolution_value = pd.to_datetime(resolution_time.iloc[0], errors="coerce") if not resolution_time.empty else pd.NaT
            time_travel = False
            if pd.notna(resolution_value) and pd.notna(first_time) and resolution_value < first_time:
                time_travel = True

            censoring_status = request_group["Censoring_Status"].dropna().iloc[0] if "Censoring_Status" in request_group.columns and not request_group["Censoring_Status"].dropna().empty else "Resolved"
            if pd.isna(resolution_value):
                if pd.notna(first_time) and (pd.Timestamp.now() - first_time) > pd.Timedelta(hours=48):
                    censoring_status = "Black-Hole"
                else:
                    censoring_status = "Observation-Window Censoring"

            related_api = api_df.copy()
            if not related_api.empty and student_id is not None:
                related_api = related_api[related_api.get("student_id", pd.Series(dtype=object)) == student_id]
                if not related_api.empty and "timestamp_ist" in related_api.columns:
                    if pd.notna(resolution_value):
                        related_api = related_api[
                            related_api["timestamp_ist"].between(first_time, resolution_value, inclusive="both")
                        ]
                    elif pd.notna(first_time):
                        related_api = related_api[related_api["timestamp_ist"] >= first_time]
            follow_up_count = int(len(related_api)) if not related_api.empty else 0

            resolution_source = None
            if "Resolution_Source" in request_group.columns:
                non_null_source = request_group["Resolution_Source"].dropna()
                resolution_source = non_null_source.iloc[0] if not non_null_source.empty else None

            has_attachment_anomaly = (
                bool(request_group["Missing_Attachment_Anomaly"].any())
                if "Missing_Attachment_Anomaly" in request_group.columns
                else False
            )

            grouped.append(
                {
                    "Request_ID": request_group["Request_ID"].iloc[0],
                    "student_id": student_id,
                    "Sender_Email": request_group["Sender_Email"].iloc[0],
                    "Submission_Timestamp": first_time,
                    "Resolution_Timestamp": resolution_value,
                    "Resolution_Source": resolution_source,
                    "Request_Count": len(request_group),
                    "Follow_Up_Count": follow_up_count,
                    "Invisible_Handoff": has_invisible_handoff,
                    "Financial_Amount": request_group["Financial_Amount"].dropna().iloc[0] if has_financial_amount else None,
                    "Needs_Follow_Up": follow_up_count > 0,
                    "Time_Travel_Anomaly": time_travel,
                    "Censoring_Status": censoring_status,
                    "Unknown_Identity": student_id == "Unknown Identity",
                    "Missing_Attachment_Anomaly": has_attachment_anomaly,
                }
            )

        summary = pd.DataFrame(grouped)
        if not summary.empty:
            summary["Submission_Timestamp"] = pd.to_datetime(summary["Submission_Timestamp"], errors="coerce")
            if "Resolution_Timestamp" in summary.columns:
                summary["Resolution_Timestamp"] = pd.to_datetime(summary["Resolution_Timestamp"], errors="coerce")
        return summary

    def calculate_kpi(self, request_summary: pd.DataFrame) -> dict[str, Any]:
        if request_summary.empty:
            return {
                "total_requests": 0,
                "resolved_without_follow_up": 0,
                "excluded_time_travel": 0,
                "excluded_censored": 0,
                "resolved_without_follow_up_pct": 0.0,
            }

        filtered = request_summary.loc[
            ~request_summary["Time_Travel_Anomaly"].fillna(False)
            & ~request_summary["Censoring_Status"].isin(["Black-Hole", "Observation-Window Censoring"])
        ].copy()

        resolved_without_follow_up = int((filtered["Needs_Follow_Up"] == False).sum())
        total = int(len(filtered))
        pct = (resolved_without_follow_up / total * 100.0) if total else 0.0

        return {
            "total_requests": int(len(request_summary)),
            "total_included_requests": total,
            "resolved_without_follow_up": resolved_without_follow_up,
            "excluded_time_travel": int(request_summary["Time_Travel_Anomaly"].fillna(False).sum()),
            "excluded_censored": int(request_summary["Censoring_Status"].isin(["Black-Hole", "Observation-Window Censoring"]).sum()),
            "black_hole_requests": int((request_summary["Censoring_Status"] == "Black-Hole").sum()),
            "observation_window_censored": int((request_summary["Censoring_Status"] == "Observation-Window Censoring").sum()),
            "unknown_identity_requests": int(request_summary["Unknown_Identity"].fillna(False).sum()) if "Unknown_Identity" in request_summary.columns else 0,
            "missing_attachment_anomaly_requests": int(request_summary["Missing_Attachment_Anomaly"].fillna(False).sum()) if "Missing_Attachment_Anomaly" in request_summary.columns else 0,
            "resolved_without_follow_up_pct": round(pct, 4),
        }

    def run_model(self) -> dict[str, Any]:
        ensure_validated_dir()
        inbox_df, directory_df, api_payload, resolution_events_df = self.load_validated_data()

        modeled = self.build_request_threads(inbox_df)
        modeled = self.parse_body_features(modeled)
        modeled = self.resolve_request_timestamps(modeled, resolution_events_df)

        request_summary = self.build_request_summary(modeled, api_payload)
        kpi = self.calculate_kpi(request_summary)

        MODELED_DIR = Path(str(MODELED_REQUESTS_OUTPUT)).parent
        MODELED_DIR.mkdir(parents=True, exist_ok=True)
        request_summary.to_csv(MODELED_REQUESTS_OUTPUT, index=False)
        with Path(MODELED_KPI_OUTPUT).open("w", encoding="utf-8") as handle:
            json.dump(kpi, handle, ensure_ascii=False, indent=2)

        return {
            "modeled_requests_path": str(MODELED_REQUESTS_OUTPUT),
            "kpi_metrics_path": str(MODELED_KPI_OUTPUT),
            "kpi": kpi,
        }


def model_all() -> dict[str, Any]:
    return WorkflowModeler().run_model()
