from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
VALIDATED_DIR = DATA_DIR / "validated"
QUARANTINE_DIR = DATA_DIR / "quarantine"

RAW_INBOX_INPUT = DATA_DIR / "raw_student_alert_inbox_final.csv"
LEGACY_RAW_INBOX_INPUT = DATA_DIR / "raw_student_alert_inbox.csv"
STUDENT_DIRECTORY_INPUT = DATA_DIR / "student_directory_master.csv"
API_INTERACTIONS_INPUT = DATA_DIR / "api_student_interactions.json"

# Resolution-event sources. These record the operational systems where a
# student's underlying issue was actually closed out (mess clearance, a
# finance dispute, an academic-credit correction). They are joined against
# the inbox/API request lifecycle in the modeling stage to determine whether
# a request was ever resolved, instead of assuming every request is
# unresolved. See findings/05_modeling_spec.md for the join rationale.
MESS_ROSTER_INPUT = DATA_DIR / "mess_roster_updates.csv"
FINANCE_DISPUTES_INPUT = DATA_DIR / "finance_fee_disputes_Q3.csv"
ACADEMIC_CREDITS_INPUT = DATA_DIR / "academic_credits_master.csv"

RAW_INBOX_OUTPUT = RAW_DIR / "raw_inbox.csv"
RAW_DIRECTORY_OUTPUT = RAW_DIR / "raw_directory.csv"
RAW_API_OUTPUT = RAW_DIR / "raw_api.json"
RAW_MESS_ROSTER_OUTPUT = RAW_DIR / "raw_mess_roster.csv"
RAW_FINANCE_DISPUTES_OUTPUT = RAW_DIR / "raw_finance_disputes.csv"
RAW_ACADEMIC_CREDITS_OUTPUT = RAW_DIR / "raw_academic_credits.csv"

VALIDATED_INBOX_OUTPUT = VALIDATED_DIR / "validated_inbox.csv"
VALIDATED_DIRECTORY_OUTPUT = VALIDATED_DIR / "validated_directory.csv"
VALIDATED_API_OUTPUT = VALIDATED_DIR / "validated_api.json"
VALIDATED_RESOLUTION_EVENTS_OUTPUT = VALIDATED_DIR / "validated_resolution_events.csv"

MODELED_DIR = DATA_DIR / "modeled"
MODELED_REQUESTS_OUTPUT = MODELED_DIR / "student_requests.csv"
MODELED_KPI_OUTPUT = MODELED_DIR / "kpi_metrics.json"

QUARANTINE_API_ERRORS_OUTPUT = QUARANTINE_DIR / "api_errors.json"
QUARANTINE_DIRECTORY_OUTPUT = QUARANTINE_DIR / "directory_duplicates.json"
QUARANTINE_INBOX_OUTPUT = QUARANTINE_DIR / "inbox_duplicates.json"
QUARANTINE_CRITICAL_NULLS_OUTPUT = QUARANTINE_DIR / "critical_nulls.csv"
QUARANTINE_RESOLUTION_EVENTS_OUTPUT = QUARANTINE_DIR / "resolution_event_nulls.csv"


def ensure_raw_dir() -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    return RAW_DIR


def ensure_validated_dir() -> Path:
    VALIDATED_DIR.mkdir(parents=True, exist_ok=True)
    return VALIDATED_DIR


def ensure_quarantine_dir() -> Path:
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    return QUARANTINE_DIR


def ensure_configured_source_files() -> None:
    if not RAW_INBOX_INPUT.exists() and LEGACY_RAW_INBOX_INPUT.exists():
        RAW_INBOX_INPUT.write_bytes(LEGACY_RAW_INBOX_INPUT.read_bytes())
