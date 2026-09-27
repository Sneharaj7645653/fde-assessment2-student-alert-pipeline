from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parent / "data" / "raw_student_alert_inbox.csv"
TARGET_MAX_TIMESTAMP = pd.Timestamp("2026-09-20 00:00:00")


def shift_dataset_to_2026(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if "Timestamp_IST" not in df.columns:
        raise KeyError("Timestamp_IST column is required in the inbox dataset.")

    ts = pd.to_datetime(df["Timestamp_IST"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    if ts.isna().all():
        raise ValueError("No valid timestamps were found in Timestamp_IST.")

    current_max = ts.max()
    shift_delta = TARGET_MAX_TIMESTAMP - current_max
    shifted_ts = ts + shift_delta

    df["Timestamp_IST"] = shifted_ts.dt.strftime("%Y-%m-%d %H:%M:%S")
    df.to_csv(csv_path, index=False)

    print(f"Original max timestamp: {current_max}")
    print(f"Target max timestamp: {TARGET_MAX_TIMESTAMP}")
    print(f"Applied delta: {shift_delta}")
    print(f"Updated dataset saved to: {csv_path}")
    print(f"New max timestamp: {pd.to_datetime(df['Timestamp_IST'], format='%Y-%m-%d %H:%M:%S').max()}")
    return df


if __name__ == "__main__":
    shift_dataset_to_2026(DATA_PATH)
