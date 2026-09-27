from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import (
    MODELED_KPI_OUTPUT,
    MODELED_REQUESTS_OUTPUT,
    QUARANTINE_CRITICAL_NULLS_OUTPUT,
    RAW_API_OUTPUT,
    RAW_DIRECTORY_OUTPUT,
    RAW_INBOX_OUTPUT,
    VALIDATED_API_OUTPUT,
    VALIDATED_DIRECTORY_OUTPUT,
    VALIDATED_INBOX_OUTPUT,
)
from src.extract import extract_all
from src.logger import get_pipeline_logger
from src.model import model_all
from src.validate import validate_all
from src.visualize import generate_business_evidence_report


class DataPipeline:
    def __init__(self) -> None:
        self.logger = get_pipeline_logger()

    @staticmethod
    def _count_rows(path: str | Path) -> int:
        file_path = Path(path)
        if not file_path.exists():
            return 0

        if file_path.suffix.lower() == ".csv":
            return len(pd.read_csv(file_path))
        if file_path.suffix.lower() == ".json":
            with file_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, list):
                return len(payload)
            if isinstance(payload, dict):
                return 1
            return 0
        return 0

    @staticmethod
    def _count_shape(path: str | Path) -> tuple[int, int]:
        file_path = Path(path)
        if not file_path.exists():
            return (0, 0)
        if file_path.suffix.lower() == ".csv":
            frame = pd.read_csv(file_path)
            return frame.shape
        if file_path.suffix.lower() == ".json":
            with file_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, list) and payload and isinstance(payload[0], dict):
                return (len(payload), len(payload[0]))
            if isinstance(payload, dict):
                return (1, len(payload))
            return (len(payload) if isinstance(payload, list) else 0, 0)
        return (0, 0)

    def _capture_phase_transition(self, phase_name: str, dataset_name: str, before_file: str | Path, after_file: str | Path) -> None:
        before_rows = self._count_rows(before_file)
        after_rows = self._count_rows(after_file)
        before_shape = self._count_shape(before_file)
        after_shape = self._count_shape(after_file)
        self.logger.log_shape_transition(
            phase_name,
            dataset_name,
            before_rows=before_rows,
            after_rows=after_rows,
            before_shape=before_shape,
            after_shape=after_shape,
        )

    def run(self) -> dict[str, Any]:
        self.logger.phase_start("EXTRACTION")
        try:
            raw_summary = extract_all()
            self.logger.info("Extraction phase completed successfully")
        except Exception as exc:
            self.logger.exception("Pipeline failed during EXTRACTION phase")
            raise RuntimeError(f"Pipeline failed during extraction: {exc}") from exc
        finally:
            self.logger.phase_end("EXTRACTION")

        before_extract_inbox = 0
        before_extract_directory = 0
        before_extract_api = 0
        if Path(RAW_INBOX_OUTPUT).exists():
            before_extract_inbox = self._count_rows(RAW_INBOX_OUTPUT)
        if Path(RAW_DIRECTORY_OUTPUT).exists():
            before_extract_directory = self._count_rows(RAW_DIRECTORY_OUTPUT)
        if Path(RAW_API_OUTPUT).exists():
            before_extract_api = self._count_rows(RAW_API_OUTPUT)

        self._capture_phase_transition("EXTRACTION -> VALIDATION", "inbox", RAW_INBOX_OUTPUT, VALIDATED_INBOX_OUTPUT)
        self._capture_phase_transition("EXTRACTION -> VALIDATION", "directory", RAW_DIRECTORY_OUTPUT, VALIDATED_DIRECTORY_OUTPUT)
        self._capture_phase_transition("EXTRACTION -> VALIDATION", "api", RAW_API_OUTPUT, VALIDATED_API_OUTPUT)

        self.logger.phase_start("VALIDATION")
        try:
            validation_summary = validate_all()
            self.logger.info("Validation phase completed successfully")
        except Exception as exc:
            self.logger.exception("Pipeline failed during VALIDATION phase")
            raise RuntimeError(f"Pipeline failed during validation: {exc}") from exc
        finally:
            self.logger.phase_end("VALIDATION")

        if Path(VALIDATED_INBOX_OUTPUT).exists() or Path(VALIDATED_DIRECTORY_OUTPUT).exists() or Path(VALIDATED_API_OUTPUT).exists():
            self._capture_phase_transition("VALIDATION -> MODELING", "inbox", VALIDATED_INBOX_OUTPUT, MODELED_REQUESTS_OUTPUT)

        self.logger.phase_start("MODELING")
        try:
            model_summary = model_all()
            self.logger.info("Modeling phase completed successfully")
        except Exception as exc:
            self.logger.exception("Pipeline failed during MODELING phase")
            raise RuntimeError(f"Pipeline failed during modeling: {exc}") from exc
        finally:
            self.logger.phase_end("MODELING")

        self._capture_phase_transition("MODELING", "student_requests", MODELED_REQUESTS_OUTPUT, MODELED_REQUESTS_OUTPUT)

        self.logger.phase_start("VISUALIZATION")
        try:
            evidence_path = generate_business_evidence_report()
            self.logger.info("Visualization phase completed successfully | output=%s", evidence_path)
        except Exception as exc:
            self.logger.exception("Pipeline failed during VISUALIZATION phase")
            raise RuntimeError(f"Pipeline failed during visualization: {exc}") from exc
        finally:
            self.logger.phase_end("VISUALIZATION")

        final_summary = {
            "status": "success",
            "extraction": raw_summary,
            "validation": validation_summary,
            "modeling": model_summary,
            "artifacts": {
                "raw_inbox": str(RAW_INBOX_OUTPUT),
                "raw_directory": str(RAW_DIRECTORY_OUTPUT),
                "raw_api": str(RAW_API_OUTPUT),
                "validated_inbox": str(VALIDATED_INBOX_OUTPUT),
                "validated_directory": str(VALIDATED_DIRECTORY_OUTPUT),
                "validated_api": str(VALIDATED_API_OUTPUT),
                "modeled_requests": str(MODELED_REQUESTS_OUTPUT),
                "kpi_metrics": str(MODELED_KPI_OUTPUT),
                "critical_nulls": str(QUARANTINE_CRITICAL_NULLS_OUTPUT),
                "business_evidence": str(evidence_path),
            },
            "data_shape": {
                "raw_inbox_rows": self._count_rows(RAW_INBOX_OUTPUT),
                "validated_inbox_rows": self._count_rows(VALIDATED_INBOX_OUTPUT),
                "modeled_requests_rows": self._count_rows(MODELED_REQUESTS_OUTPUT),
            },
        }

        self.logger.info("PIPELINE COMPLETE | status=success")
        return final_summary


def run_pipeline() -> dict[str, Any]:
    return DataPipeline().run()


if __name__ == "__main__":
    run_pipeline()
