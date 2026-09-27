from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.config import (
    API_INTERACTIONS_INPUT,
    RAW_API_OUTPUT,
    RAW_DIRECTORY_OUTPUT,
    RAW_INBOX_INPUT,
    RAW_INBOX_OUTPUT,
    STUDENT_DIRECTORY_INPUT,
    ensure_configured_source_files,
)
from src.extract import DataExtractor


@pytest.fixture
def extractor() -> DataExtractor:
    ensure_configured_source_files()
    return DataExtractor(
        raw_inbox_path=RAW_INBOX_INPUT,
        directory_path=STUDENT_DIRECTORY_INPUT,
        api_path=API_INTERACTIONS_INPUT,
    )


def test_extract_csv_files_preserve_row_counts_and_columns(extractor: DataExtractor) -> None:
    inbox_df = extractor.extract_csv(RAW_INBOX_INPUT)
    directory_df = extractor.extract_csv(STUDENT_DIRECTORY_INPUT)

    assert isinstance(inbox_df, pd.DataFrame)
    assert isinstance(directory_df, pd.DataFrame)
    assert len(inbox_df) > 0
    assert len(directory_df) > 0

    assert inbox_df.shape[0] == pd.read_csv(RAW_INBOX_INPUT).shape[0]
    assert directory_df.shape[0] == pd.read_csv(STUDENT_DIRECTORY_INPUT).shape[0]
    assert inbox_df.shape[1] == pd.read_csv(RAW_INBOX_INPUT).shape[1]
    assert directory_df.shape[1] == pd.read_csv(STUDENT_DIRECTORY_INPUT).shape[1]

    loaded = extractor.extract_all()
    assert len(loaded["inbox"]) == len(inbox_df)
    assert len(loaded["directory"]) == len(directory_df)

    assert RAW_INBOX_OUTPUT.exists()
    assert RAW_DIRECTORY_OUTPUT.exists()
    assert RAW_API_OUTPUT.exists()


def test_extract_json_handles_mixed_schema_error_envelopes(extractor: DataExtractor) -> None:
    payload = extractor.extract_json(API_INTERACTIONS_INPUT)

    assert isinstance(payload, list)
    assert len(payload) > 0

    error_record = next((item for item in payload if isinstance(item, dict) and "error" in item), None)
    assert error_record is not None
    assert error_record["error"] == "500 Internal Server Error"

    normal_record = next(
        (item for item in payload if isinstance(item, dict) and "interaction_id" in item),
        None,
    )
    assert normal_record is not None
    assert "student_id" in normal_record
    assert "timestamp_ist" in normal_record

    raw_api = json.loads(RAW_API_OUTPUT.read_text(encoding="utf-8"))
    assert isinstance(raw_api, list)
    assert len(raw_api) == len(payload)
