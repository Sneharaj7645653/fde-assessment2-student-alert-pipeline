from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
LOG_PATH = DATA_DIR / "pipeline.log"


class PipelineLogger:
    def __init__(self, name: str = "fde_pipeline") -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        if not self.logger.handlers:
            formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)

            file_handler = logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8")
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)

            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.logger.error(message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.logger.exception(message, *args, **kwargs)

    def phase_start(self, phase_name: str) -> None:
        self.info("PHASE START | %s", phase_name)

    def phase_end(self, phase_name: str, status: str = "success") -> None:
        self.info("PHASE END | %s | status=%s", phase_name, status)

    def log_shape_transition(
        self,
        phase_name: str,
        dataset_name: str,
        before_rows: int | None = None,
        after_rows: int | None = None,
        before_shape: tuple[int, int] | None = None,
        after_shape: tuple[int, int] | None = None,
    ) -> None:
        before_text = f"rows={before_rows}" if before_rows is not None else "rows=unknown"
        after_text = f"rows={after_rows}" if after_rows is not None else "rows=unknown"
        before_shape_text = f"shape={before_shape}" if before_shape is not None else "shape=unknown"
        after_shape_text = f"shape={after_shape}" if after_shape is not None else "shape=unknown"
        self.info(
            "%s | %s | %s -> %s | %s -> %s",
            phase_name,
            dataset_name,
            before_text,
            after_text,
            before_shape_text,
            after_shape_text,
        )


def get_pipeline_logger() -> PipelineLogger:
    return PipelineLogger()


LOGGER = get_pipeline_logger()
