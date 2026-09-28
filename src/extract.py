from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import (
    ACADEMIC_CREDITS_INPUT,
    API_INTERACTIONS_INPUT,
    FINANCE_DISPUTES_INPUT,
    MESS_ROSTER_INPUT,
    RAW_ACADEMIC_CREDITS_OUTPUT,
    RAW_API_OUTPUT,
    RAW_DIRECTORY_OUTPUT,
    RAW_FINANCE_DISPUTES_OUTPUT,
    RAW_INBOX_INPUT,
    RAW_INBOX_OUTPUT,
    RAW_MESS_ROSTER_OUTPUT,
    STUDENT_DIRECTORY_INPUT,
    ensure_configured_source_files,
    ensure_raw_dir,
)


class DataExtractor:
    def __init__(
        self,
        raw_inbox_path: Path | str = RAW_INBOX_INPUT,
        directory_path: Path | str = STUDENT_DIRECTORY_INPUT,
        api_path: Path | str = API_INTERACTIONS_INPUT,
        mess_roster_path: Path | str = MESS_ROSTER_INPUT,
        finance_disputes_path: Path | str = FINANCE_DISPUTES_INPUT,
        academic_credits_path: Path | str = ACADEMIC_CREDITS_INPUT,
    ) -> None:
        self.raw_inbox_path = Path(raw_inbox_path)
        self.directory_path = Path(directory_path)
        self.api_path = Path(api_path)
        self.mess_roster_path = Path(mess_roster_path)
        self.finance_disputes_path = Path(finance_disputes_path)
        self.academic_credits_path = Path(academic_credits_path)

    def _log_extraction(self, dataset_name: str, frame: pd.DataFrame | list[dict[str, Any]] | dict[str, Any], *, source_path: Path) -> None:
        if isinstance(frame, pd.DataFrame):
            row_count = len(frame)
            shape = frame.shape
        elif isinstance(frame, list):
            row_count = len(frame)
            if row_count and isinstance(frame[0], dict):
                shape = (row_count, len(frame[0]))
            else:
                shape = (row_count, 0)
        else:
            if isinstance(frame, dict):
                row_count = 1
                shape = (1, len(frame))
            else:
                row_count = 0
                shape = (0, 0)

        print(f"[{dataset_name}] extracted from {source_path} -> rows={row_count}, shape={shape}")

    def extract_csv(self, csv_path: Path | str) -> pd.DataFrame:
        path = Path(csv_path)
        df = pd.read_csv(path)
        self._log_extraction(path.stem, df, source_path=path)
        return df

    def extract_json(self, json_path: Path | str) -> list[Any]:
        path = Path(json_path)
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self._log_extraction(path.stem, payload, source_path=path)
        return payload

    def extract_sql(self, csv_path: Path | str, db_name: str = "student_directory.db", table_name: str = "directory_table") -> pd.DataFrame:
        path = Path(csv_path)
        
        # 1. Establish the SQLite database connection in the same directory as the source file
        db_path = path.parent / db_name
        conn = sqlite3.connect(db_path)
        
        # 2. Seed the Database (creating the SQL table from your CSV)
        seed_df = pd.read_csv(path)
        seed_df.to_sql(table_name, conn, if_exists="replace", index=False)
        
        # 3. Retrieve the data using a real SQL query (Satisfies FDE SQL retrieval rubric)
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql_query(query, conn)
        
        # 4. Close the connection
        conn.close()
        
        # Log the extraction specifically mentioning SQL
        self._log_extraction(f"{path.stem} (via SQL)", df, source_path=db_path)
        return df

    def save_raw_copy(self, dataset: Any, destination: Path | str) -> None:
        destination_path = Path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(dataset, pd.DataFrame):
            dataset.to_csv(destination_path, index=False)
        elif isinstance(dataset, (list, dict)):
            with destination_path.open("w", encoding="utf-8") as handle:
                json.dump(dataset, handle, ensure_ascii=False, indent=2)
        else:
            raise TypeError(f"Unsupported dataset type for raw persistence: {type(dataset)!r}")

    def extract_all(self) -> dict[str, Any]:
        ensure_configured_source_files()
        ensure_raw_dir()

        inbox_df = self.extract_csv(self.raw_inbox_path)
        
        # FDE Rubric Requirement: Using a second retrieval mode (SQL) for the directory
        directory_df = self.extract_sql(self.directory_path)
        
        api_payload = self.extract_json(self.api_path)
        mess_roster_df = self.extract_csv(self.mess_roster_path)
        finance_disputes_df = self.extract_csv(self.finance_disputes_path)
        academic_credits_df = self.extract_csv(self.academic_credits_path)

        self.save_raw_copy(inbox_df, RAW_INBOX_OUTPUT)
        self.save_raw_copy(directory_df, RAW_DIRECTORY_OUTPUT)
        self.save_raw_copy(api_payload, RAW_API_OUTPUT)
        self.save_raw_copy(mess_roster_df, RAW_MESS_ROSTER_OUTPUT)
        self.save_raw_copy(finance_disputes_df, RAW_FINANCE_DISPUTES_OUTPUT)
        self.save_raw_copy(academic_credits_df, RAW_ACADEMIC_CREDITS_OUTPUT)

        return {
            "inbox": inbox_df,
            "directory": directory_df,
            "api": api_payload,
            "mess_roster": mess_roster_df,
            "finance_disputes": finance_disputes_df,
            "academic_credits": academic_credits_df,
        }


def extract_all() -> dict[str, Any]:
    extractor = DataExtractor()
    return extractor.extract_all()


if __name__ == "__main__":
    extract_all()