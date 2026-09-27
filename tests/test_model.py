import pandas as pd
import pytest

from src.model import WorkflowModeler


def test_groups_same_user_emails_within_48_hours_into_one_request() -> None:
    modeler = WorkflowModeler()
    inbox = pd.DataFrame(
        [
            {
                "Sender_Email": "student.1@university.edu",
                "Timestamp_IST": "2026-09-01 08:00:00",
                "Body": "Please review my request.",
                "student_id": "24bcs10001",
            },
            {
                "Sender_Email": "student.1@university.edu",
                "Timestamp_IST": "2026-09-02 10:00:00",
                "Body": "Follow-up on the same issue.",
                "student_id": "24bcs10001",
            },
            {
                "Sender_Email": "student.2@university.edu",
                "Timestamp_IST": "2026-09-03 04:00:00",
                "Body": "Different issue.",
                "student_id": "24bcs10002",
            },
        ]
    )

    grouped = modeler.build_request_threads(inbox)
    assert grouped["Request_ID"].nunique() == 2
    assert grouped.loc[0, "Request_ID"] == grouped.loc[1, "Request_ID"]
    assert grouped.loc[1, "Request_ID"] != grouped.loc[2, "Request_ID"]


def test_follow_up_api_interaction_counts_as_follow_up() -> None:
    modeler = WorkflowModeler()
    request_summary = pd.DataFrame(
        [
            {
                "Request_ID": "REQ-1",
                "student_id": "24bcs10001",
                "Sender_Email": "student.1@university.edu",
                "Submission_Timestamp": pd.Timestamp("2026-09-01 08:00:00"),
                "Resolution_Timestamp": pd.Timestamp("2026-09-05 08:00:00"),
                "Time_Travel_Anomaly": False,
                "Censoring_Status": "Resolved",
            }
        ]
    )
    api_payload = [
        {
            "student_id": "24bcs10001",
            "interaction_type": "Phone Call",
            "timestamp_ist": "2026-09-02 09:00:00",
        },
        {
            "student_id": "24bcs10001",
            "interaction_type": "Walk-in",
            "timestamp_ist": "2026-09-04 09:00:00",
        },
    ]

    summary = modeler.build_request_summary(
        pd.DataFrame(
            [
                {
                    "Request_ID": "REQ-1",
                    "Timestamp_IST": pd.Timestamp("2026-09-01 08:00:00"),
                    "Sender_Email": "student.1@university.edu",
                    "student_id": "24bcs10001",
                    "Invisible_Handoff": False,
                    "Financial_Amount": None,
                    "Time_Travel_Anomaly": False,
                    "Censoring_Status": "Resolved",
                    "Resolution_Timestamp": pd.Timestamp("2026-09-05 08:00:00"),
                }
            ]
        ),
        api_payload,
    )

    assert summary.loc[0, "Follow_Up_Count"] == 2
    assert bool(summary.loc[0, "Needs_Follow_Up"]) is True


def test_build_request_summary_flags_a_resolution_that_predates_submission() -> None:
    # If a matched resolution event somehow precedes the request's own
    # submission timestamp, build_request_summary must flag it as a
    # Time_Travel_Anomaly rather than silently accepting an impossible
    # lifecycle (resolution_value < first_time).
    modeler = WorkflowModeler()
    modeled = pd.DataFrame(
        [
            {
                "Request_ID": "REQ-9",
                "Timestamp_IST": pd.Timestamp("2026-09-05 08:00:00"),
                "Sender_Email": "student.1@university.edu",
                "student_id": "24bcs10001",
                "Invisible_Handoff": False,
                "Financial_Amount": None,
                "Resolution_Timestamp": pd.Timestamp("2026-09-04 16:00:00"),
                "Resolution_Source": "academic_credits",
            }
        ]
    )

    summary = modeler.build_request_summary(modeled, api_payload=[])

    assert bool(summary.loc[0, "Time_Travel_Anomaly"]) is True


class TestResolveRequestTimestamps:
    """Regression coverage for the core defect found in review:
    resolve_request_timestamps() used to hardcode Resolution_Timestamp=NaT
    for every request unconditionally, which made every request fall into
    Black-Hole/Observation-Window Censoring and get excluded from the KPI
    (data/modeled/kpi_metrics.json showed total_included_requests: 0). The
    fix joins mess-roster/finance-dispute/academic-credit resolution events
    onto each request thread, keyed by student_id and matched by time.
    """

    @staticmethod
    def _modeled_inbox(rows: list[dict]) -> pd.DataFrame:
        df = pd.DataFrame(rows)
        df["Timestamp_IST"] = pd.to_datetime(df["Timestamp_IST"])
        return df

    def test_request_is_matched_to_the_earliest_resolution_event_after_submission(self) -> None:
        modeler = WorkflowModeler()
        modeled = self._modeled_inbox(
            [
                {
                    "Request_ID": "REQ-1",
                    "Sender_Email": "student.1@university.edu",
                    "student_id": "24bcs10001",
                    "Timestamp_IST": "2026-08-01 08:00:00",
                }
            ]
        )
        resolution_events = pd.DataFrame(
            [
                {
                    "student_id": "24bcs10001",
                    "resolution_timestamp": pd.Timestamp("2026-07-01 00:00:00"),  # before submission: ignored
                    "resolution_state": "Cleared",
                    "source_system": "mess_roster",
                },
                {
                    "student_id": "24bcs10001",
                    "resolution_timestamp": pd.Timestamp("2026-08-03 00:00:00"),  # first valid candidate
                    "resolution_state": "Closed",
                    "source_system": "finance_disputes",
                },
                {
                    "student_id": "24bcs10001",
                    "resolution_timestamp": pd.Timestamp("2026-08-05 00:00:00"),
                    "resolution_state": "Done",
                    "source_system": "academic_credits",
                },
            ]
        )

        resolved = modeler.resolve_request_timestamps(modeled, resolution_events)

        assert resolved.loc[0, "Resolution_Timestamp"] == pd.Timestamp("2026-08-03 00:00:00")
        assert resolved.loc[0, "Resolution_Source"] == "finance_disputes"

    def test_a_resolution_event_is_never_reused_across_two_requests_from_the_same_student(self) -> None:
        modeler = WorkflowModeler()
        modeled = self._modeled_inbox(
            [
                {
                    "Request_ID": "REQ-1",
                    "Sender_Email": "student.1@university.edu",
                    "student_id": "24bcs10001",
                    "Timestamp_IST": "2026-08-01 08:00:00",
                },
                {
                    "Request_ID": "REQ-2",
                    "Sender_Email": "student.1@university.edu",
                    "student_id": "24bcs10001",
                    "Timestamp_IST": "2026-08-10 08:00:00",
                },
            ]
        )
        # Only one resolution event exists for this student.
        resolution_events = pd.DataFrame(
            [
                {
                    "student_id": "24bcs10001",
                    "resolution_timestamp": pd.Timestamp("2026-08-02 00:00:00"),
                    "resolution_state": "Cleared",
                    "source_system": "mess_roster",
                }
            ]
        )

        resolved = modeler.resolve_request_timestamps(modeled, resolution_events)
        by_request = resolved.set_index("Request_ID")

        assert by_request.loc["REQ-1", "Resolution_Timestamp"] == pd.Timestamp("2026-08-02 00:00:00")
        assert pd.isna(by_request.loc["REQ-2", "Resolution_Timestamp"])

    def test_request_with_no_matching_resolution_event_stays_unresolved(self) -> None:
        modeler = WorkflowModeler()
        modeled = self._modeled_inbox(
            [
                {
                    "Request_ID": "REQ-1",
                    "Sender_Email": "student.unknown@university.edu",
                    "student_id": "24bcs99999",
                    "Timestamp_IST": "2026-08-01 08:00:00",
                }
            ]
        )
        resolution_events = pd.DataFrame(
            columns=["student_id", "resolution_timestamp", "resolution_state", "source_system"]
        )

        resolved = modeler.resolve_request_timestamps(modeled, resolution_events)

        assert pd.isna(resolved.loc[0, "Resolution_Timestamp"])
        assert resolved.loc[0, "Resolution_Source"] is None

    def test_end_to_end_kpi_reflects_confirmed_resolutions_not_a_degenerate_zero(self) -> None:
        modeler = WorkflowModeler()
        modeled = self._modeled_inbox(
            [
                {
                    "Request_ID": "REQ-RESOLVED",
                    "Sender_Email": "student.1@university.edu",
                    "student_id": "24bcs10001",
                    "Timestamp_IST": "2020-01-01 08:00:00",
                    "Body": "issue",
                },
                {
                    "Request_ID": "REQ-BLACKHOLE",
                    "Sender_Email": "student.2@university.edu",
                    "student_id": "24bcs10002",
                    "Timestamp_IST": "2020-01-01 08:00:00",
                    "Body": "issue",
                },
            ]
        )
        modeled = modeler.parse_body_features(modeled)
        resolution_events = pd.DataFrame(
            [
                {
                    "student_id": "24bcs10001",
                    "resolution_timestamp": pd.Timestamp("2020-01-02 00:00:00"),
                    "resolution_state": "Cleared",
                    "source_system": "mess_roster",
                }
            ]
        )

        resolved = modeler.resolve_request_timestamps(modeled, resolution_events)
        summary = modeler.build_request_summary(resolved, api_payload=[])
        kpi = modeler.calculate_kpi(summary)

        # The old bug made this permanently 0/0 regardless of input.
        assert kpi["total_included_requests"] == 1
        assert kpi["resolved_without_follow_up"] == 1
        assert kpi["resolved_without_follow_up_pct"] == pytest.approx(100.0)
        assert kpi["black_hole_requests"] == 1
