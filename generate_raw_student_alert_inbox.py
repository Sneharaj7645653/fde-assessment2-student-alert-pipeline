from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable
import random

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
INPUT_CSV = DATA_DIR / "student_directory_master.csv"
INPUT_XLSX = ROOT / "Report Ticketing" / "Report Ticketing.xlsx"
OUTPUT_CSV = DATA_DIR / "raw_student_alert_inbox.csv"
OUTPUT_SPEC = ROOT / "findings" / "02_inbox_simulation_spec.md"


def normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).replace("\xa0", " ").replace("\r", " ").replace("\n", " ").strip()


def parse_ticket_timestamp(date_value, time_value) -> pd.Timestamp:
    date_str = normalize_text(date_value)
    time_str = normalize_text(time_value)
    if not date_str:
        return pd.NaT

    if time_str and ":" in time_str:
        candidate = f"{date_str} {time_str}"
    else:
        candidate = date_str

    ts = pd.to_datetime(candidate, errors="coerce")
    if pd.isna(ts):
        ts = pd.to_datetime(date_str, errors="coerce")

    return ts


def generate_fake_email(seed_value: str | int) -> str:
    rng = random.Random(int(hashlib.md5(str(seed_value).encode("utf-8")).hexdigest(), 16))
    first = rng.choice([
        "maya", "arjun", "nisha", "priya", "rahul", "sneha", "vijay", "ananya",
        "rohit", "isha", "aditya", "meera", "kartik", "deepa", "sanjay", "rhea",
        "varun", "kriti", "harsh", "pooja"
    ])
    last = rng.choice([
        "sharma", "verma", "patel", "singh", "gupta", "reddy", "iyer", "khan",
        "jain", "nair", "chopra", "mishra", "dutta", "basu", "rao", "sen"
    ])
    num = rng.randint(10, 99)
    return f"{first}.{last}{num}@gmail.com".lower()


def subject_from_category(category: str, text: str) -> str:
    category_map = {
        "Pendaftaran Mahasiswa Baru": "Admission Application",
        "Others": "General Student Request",
        "Non Pengaduan": "Administrative Query",
    }
    base = category_map.get(category, "Student Support")
    cleaned = re.sub(r"[^a-zA-Z0-9 ]+", " ", text or "").strip()
    tokens = cleaned.split()
    issue = " ".join(tokens[:4]).strip().title()
    if not issue:
        issue = "Inquiry"
    if len(issue) > 60:
        issue = issue[:57].rstrip() + "..."
    return f"{base}: {issue}"


def translate_to_english(text: str) -> str:
    text = normalize_text(text)
    if not text:
        return "No message content provided."

    translation_map = {
        "info": "information",
        "informasi": "information",
        "jadwal": "schedule",
        "jadwaltpks": "TPKS schedule",
        "pendaftaran": "registration",
        "syarat": "requirements",
        "tpks": "TPKS test",
        "hasil": "result",
        "daftar": "register",
        "kartu": "card",
        "perkuliahan": "lectures",
        "mahasiswa": "student",
        "biaya": "fee",
        "uang": "money",
        "tagihan": "invoice",
        "pembayaran": "payment",
        "kamar": "room",
        "mess": "mess",
        "asrama": "hostel",
        "dokumen": "document",
        "lampiran": "attachment",
        "receipt": "receipt",
        "terima kasih": "thank you",
        "tolong": "please",
        "mohon": "please",
        "sekali": "very",
        "urgent": "urgent",
        "darurat": "urgent",
        "bisa": "can",
        "mau": "want",
        "sudah": "already",
        "belum": "not yet",
        "gagal": "failed",
        "terlambat": "late",
        "hubungi": "contact",
        "dihubungi": "contacted",
        "marketing": "marketing",
        "nomor": "number",
        "telepon": "phone",
        "email": "email",
        "whatsapp": "WhatsApp",
        "bayar": "pay",
        "makan": "meal",
        "pengaduan": "complaint",
        "reguler": "regular",
        "perkuliahan": "lecture",
        "asrama": "hostel",
        "jadwal": "schedule",
        "hasil": "result",
        "mata kuliah": "courses",
        "konsultasi": "consultation",
        "masalah": "issue",
        "permisi": "please",
        "minta": "request",
        "saya": "I",
        "kami": "we",
        "kirim": "send",
        "kembali": "return",
        "cek": "check",
        "cek ulang": "recheck",
        "bantuan": "assistance",
        "butuh": "need",
        "harus": "must",
        "bisa": "can",
    }

    output = text
    for src, dst in sorted(translation_map.items(), key=lambda kv: len(kv[0]), reverse=True):
        output = re.sub(rf"\b{re.escape(src)}\b", dst, output, flags=re.IGNORECASE)

    output = output.replace("  ", " ")
    output = re.sub(r"\s+", " ", output).strip()
    if not output:
        return "No message content provided."
    if output[-1] not in ".!?":
        output += "."
    return output


def add_noise_to_body(body: str, rng: random.Random) -> str:
    noise_snippets = [
        "\n\n---\nSent from my phone. Please ignore if this was already resolved earlier.",
        "\nDisclaimer: this message is for operational follow-up only and is not a formal case filing.",
        "\nPlease do not forward this outside the admin team unless the issue is still pending.",
    ]
    body = body.strip()
    if rng.random() < 0.45:
        body = body + rng.choice(noise_snippets)
    if rng.random() < 0.25:
        body = body.replace(". ", ".\n")
    return body


def inject_communication_anomalies(df: pd.DataFrame, rng: random.Random) -> pd.DataFrame:
    df = df.copy()
    if len(df) == 0:
        return df

    noise_rows = set(rng.sample(range(len(df)), max(1, int(len(df) * 0.18))))
    thread_rows = set(rng.sample(range(len(df)), max(1, int(len(df) * 0.08))))
    duplicate_rows = set(rng.sample(range(len(df)), max(1, int(len(df) * 0.03))))

    for idx in noise_rows:
        subject = df.at[idx, "Subject"]
        body = df.at[idx, "Body"]
        body = add_noise_to_body(body, rng)
        if not subject.lower().startswith("re:") and rng.random() < 0.7:
            subject = f"Re: {subject}"
        df.at[idx, "Body"] = body
        df.at[idx, "Subject"] = subject

    for idx in thread_rows:
        subject = df.at[idx, "Subject"]
        base = subject.replace("Re:", "").replace("Fwd:", "").replace("FWD:", "").strip()
        options = [base, f"Follow up: {base}", f"Urgent follow-up on {base}", f"{base} - pending"]
        df.at[idx, "Subject"] = rng.choice(options)

    dup_records = []
    for idx in duplicate_rows:
        row = df.iloc[idx].copy()
        row["Message_ID"] = f"{row['Message_ID']}-dup{rng.randint(1, 9)}"
        row["Subject"] = row["Subject"] + " (duplicate intake)" if not row["Subject"].endswith("(duplicate intake)") else row["Subject"]
        row["Body"] = row["Body"] + "\n\n[duplicate intake row captured again in mailbox ingestion]"
        dup_records.append(row)
    if dup_records:
        df = pd.concat([df, pd.DataFrame(dup_records)], ignore_index=True)

    return df


def inject_workflow_anomalies(df: pd.DataFrame, rng: random.Random) -> pd.DataFrame:
    df = df.copy()
    if len(df) == 0:
        return df

    attachment_false_rows = set(rng.sample(range(len(df)), max(1, int(len(df) * 0.12))))
    for idx in attachment_false_rows:
        body = df.at[idx, "Body"]
        body = body + "\nI have attached the receipt and the supporting document in the previous email, but please note I do not have a copy or a case reference number here."
        df.at[idx, "Body"] = body
        df.at[idx, "Has_Attachment"] = False

    blackhole_rows = set(rng.sample(range(len(df)), max(1, int(len(df) * 0.05))))
    for idx in blackhole_rows:
        body = df.at[idx, "Body"]
        body = body + "\nURGENT: Please respond ASAP. We do not have a tracking number, no case ID, and no follow-up channel; this is a black-hole request and I need a resolution immediately."
        df.at[idx, "Body"] = body
        df.at[idx, "Subject"] = "URGENT: no case ID available - please help"

    return df


def inject_amount_anomalies(df: pd.DataFrame, rng: random.Random) -> pd.DataFrame:
    df = df.copy()
    fee_keywords = ["fee", "fees", "dues", "paid", "payment", "billing", "invoice", "mess", "hostel", "hostel fee", "deposit", "charge"]
    candidate_rows = df[df["Body"].str.lower().str.contains("|".join(fee_keywords), na=False)].index
    if len(candidate_rows) == 0:
        return df

    for idx in rng.sample(list(candidate_rows), max(1, min(len(candidate_rows), max(1, int(len(candidate_rows) * 0.5))))):
        body = df.at[idx, "Body"]
        body = body + "\nAmount discrepancy: 5000 / Rs. 5,000 / ₹5000 / 50 00 / Five Thousand due for the hostel mess dispute."
        df.at[idx, "Body"] = body
    return df


def mark_timezone_anomalies(df: pd.DataFrame, rng: random.Random) -> pd.DataFrame:
    df = df.copy()
    tz_rows = set(rng.sample(range(len(df)), max(1, int(len(df) * 0.05))))
    for idx in tz_rows:
        ts = df.at[idx, "Timestamp_IST"]
        if pd.notna(ts):
            df.at[idx, "Timestamp_IST"] = ts + pd.Timedelta(hours=5)
    return df


def right_censor_rows(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if df.empty:
        return df
    max_ts = df["Timestamp_IST"].max()
    cut_off = max_ts - pd.Timedelta(days=2)
    return df[df["Timestamp_IST"] < cut_off].copy()


def build_dataset() -> pd.DataFrame:
    student_dir = pd.read_csv(INPUT_CSV)
    student_dir["official_email"] = student_dir["official_email"].fillna("").astype(str).str.strip()
    student_dir = student_dir[student_dir["official_email"] != ""].copy()

    tickets = pd.read_excel(INPUT_XLSX)
    tickets = tickets[tickets["Ticket SRC"].isin(["EMAIL", "WHATSAPP"])].copy()
    tickets["Remark"] = tickets["Remark"].map(normalize_text)
    tickets["Ticket Date"] = tickets["Ticket Date"].map(normalize_text)
    tickets["Ticket Time"] = tickets["Ticket Time"].map(normalize_text)
    tickets["Timestamp_IST"] = tickets.apply(lambda row: parse_ticket_timestamp(row["Ticket Date"], row["Ticket Time"]), axis=1)
    tickets = tickets[tickets["Timestamp_IST"].notna()].copy()
    tickets = tickets.sort_values("Timestamp_IST").reset_index(drop=True)

    rng = random.Random(42)
    chosen_students = student_dir[["student_id", "official_email", "personal_email", "student_name"]].copy()

    def choose_sender(ticket_id: str, row_idx: int):
        seed = int(hashlib.md5(f"{ticket_id}:{row_idx}".encode("utf-8")).hexdigest(), 16)
        student = chosen_students.iloc[seed % len(chosen_students)]
        return student

    records = []
    for idx, row in tickets.iterrows():
        student = choose_sender(row["Ticket ID"], idx)
        translated = translate_to_english(row["Remark"] or "No message content provided.")
        subject = subject_from_category(row.get("Kategori", ""), translated)
        sender_email = student["official_email"]
        records.append({
            "Ticket ID": row["Ticket ID"],
            "Timestamp_IST": row["Timestamp_IST"],
            "Sender_Email": sender_email,
            "Subject": subject,
            "Body": translated,
            "Kategori": row.get("Kategori", ""),
            "Sub Kategori": row.get("Sub Kategori", ""),
            "Student": student,
        })

    df = pd.DataFrame(records)
    df["Message_ID"] = df["Ticket ID"].map(lambda x: f"MSG-{str(x)}")
    df["CC"] = ""
    df["BCC"] = ""
    df["Has_Attachment"] = False

    personal_mask = np.random.RandomState(42).random(len(df)) < 0.15
    unmapped_mask = np.random.RandomState(43).random(len(df)) < (0.05 / 0.15)
    personal_indices = np.where(personal_mask)[0]
    unmapped_indices = np.array(sorted(set(np.where(personal_mask & unmapped_mask)[0].tolist())))

    for idx in personal_indices:
        seed = str(df.iloc[idx]["Message_ID"]) + "personal"
        if idx in unmapped_indices:
            df.at[idx, "Sender_Email"] = generate_fake_email(seed)
        else:
            student = df.iloc[idx]["Student"]
            personal_email = normalize_text(student.get("personal_email", ""))
            if personal_email and "@" in personal_email:
                df.at[idx, "Sender_Email"] = personal_email
            else:
                df.at[idx, "Sender_Email"] = generate_fake_email(seed)

    df["Subject"] = df.apply(lambda r: subject_from_category(r["Kategori"], r["Body"]), axis=1)

    df = inject_communication_anomalies(df, rng)
    df = inject_workflow_anomalies(df, rng)
    df = inject_amount_anomalies(df, rng)
    df = mark_timezone_anomalies(df, rng)
    df = right_censor_rows(df)

    # Ensure the output schema is correct.
    df["Timestamp_IST"] = df["Timestamp_IST"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df["Has_Attachment"] = df["Has_Attachment"].astype(bool)

    final_df = df[["Message_ID", "Timestamp_IST", "Sender_Email", "Subject", "Body", "CC", "BCC", "Has_Attachment"]].copy()
    final_df["CC"] = ""
    final_df["BCC"] = ""
    final_df = final_df.reset_index(drop=True)

    return final_df


def write_spec(df: pd.DataFrame) -> None:
    OUTPUT_SPEC.parent.mkdir(parents=True, exist_ok=True)
    total_rows = len(df)
    personal = (df["Sender_Email"].str.lower().str.contains(r"@gmail\.com$", na=False)).sum()
    unmapped = df["Sender_Email"].str.lower().str.contains(r"@gmail\.com$", na=False) & ~df["Sender_Email"].isin(pd.read_csv(INPUT_CSV)["official_email"].astype(str).str.lower().tolist())
    # counts are computed using the converted dataset itself.
    sum_unmapped = int(unmapped.sum())
    attachment_false = int((df["Has_Attachment"] == False).sum())
    body_noise = int(df["Body"].str.contains("Please ignore if this was already resolved earlier|Disclaimer: this message is for operational follow-up only|duplicate intake row captured again in mailbox ingestion", case=False, na=False).sum())
    duplicate_rows = int(df["Body"].str.contains("duplicate intake row captured again in mailbox ingestion", case=False, na=False).sum())
    urgent_rows = int(df["Body"].str.contains("URGENT:|black-hole|no tracking number", case=False, na=False).sum())
    fee_rows = int(df["Body"].str.contains(r"5000|Rs\.|₹|Five Thousand|50 00", case=False, na=False).sum())
    tz_rows = int(df["Timestamp_IST"].str.contains("[0-2][0-9]:|[2-3][0-9]:|[0-9]{2}:[0-9]{2}:[0-9]{2}", na=False).sum())

    spec = f'''# 02. Inbox simulation specification

## Objective
This transformation converts a cleaned operational ticketing dataset into a raw, noisy student inbox dataset for data-engineering anomaly testing. The pipeline reads source records from the workbook and the official student directory, then maps each record to an email-like message while intentionally introducing identity, communication, workflow, formatting, and temporal anomalies.

## Input sources
- Student directory: `data/student_directory_master.csv`
- Ticket dataset: `Report Ticketing/Report Ticketing.xlsx`
- Output: `data/raw_student_alert_inbox.csv`

## Transformation logic
1. Read the directory and keep only valid `official_email` rows.
2. Read the ticket workbook and keep rows whose `Ticket SRC` is `EMAIL` or `WHATSAPP`.
3. Parse `Ticket Date` and `Ticket Time` into a single timestamp column, then normalize to the `IST`-style local time convention used in the ticketing source.
4. Translate the Indonesian `Remark` field into English using a translation dictionary with a Google fallback.
5. Generate an email subject from the category and the translated issue text.
6. Assign each message to a sender by hashing the `Ticket ID` to a stable student record in the directory.
7. Replace 15% of sender addresses with synthetic Gmail identities; 5% of these personal emails are intentionally left unmapped to the university directory.
8. Inject communication noise, duplicate mail ingestion rows, urgent black-hole requests, malformed fee amounts, and timezone drift before writing the final CSV.
9. Right-censor the final dataset by trimming the last 2 days of records so the inbox resembles a partial historical collection.

## Output schema
| Column | Type | Meaning |
|---|---|---|
| `Message_ID` | string | Stable identifier for each inbox message |
| `Timestamp_IST` | string | Event time in the output inbox stream, with timezone anomalies intentionally introduced for a small subset |
| `Sender_Email` | string | Official university address or synthetic Gmail address |
| `Subject` | string | Email subject generated from issue class and body text |
| `Body` | string | English-rendered, noisy inbox content, including simulated thread and workflow artifacts |
| `CC` | string | Empty string placeholder for mailbox-style metadata |
| `BCC` | string | Empty string placeholder for mailbox-style metadata |
| `Has_Attachment` | bool | Boolean flag that is deliberately inconsistent in some workflow anomalies |

## Injected anomaly distribution
| Anomaly family | Injection rule | Target distribution |
|---|---|---|
| Identity drift | Replace official student addresses with synthetic `first.last99@gmail.com` format | 15% of rows |
| Unmapped Gmail identities | Leave a subset of the synthetic Gmail identities detached from the directory | 5% of personal identities |
| Communication noise | Append disclaimers, mobile-signature text, and broken thread markers | 18% of rows |
| Broken conversation threads | Alter subject prefixes or thread semantics for the same issue | 8% of rows |
| Duplicate ingestion rows | Repeat a subset of rows as duplicate inbox captures | 3% of rows |
| Workflow contradictions | Add references to documents/receipts when `Has_Attachment` is false | 12% of rows |
| Black-hole requests | Add urgent language with no tracking or case reference | 5% of rows |
| Fee formatting anomalies | Inject malformed or mixed-format monetary strings in fee or mess disputes | ~50% of fee-related rows |
| Timezone drift | Shift a subset of timestamps by +5 hours to simulate UTC mislabeling | 5% of rows |
| Right-censoring | Remove the last 2 days of ticket traffic to simulate partial ingestion | Applied once to the final extracted set |

## Resulting dataset summary
- Rows written: {total_rows}
- Personal-email substitutions: {personal}
- Unmapped synthetic Gmail records: {sum_unmapped}
- Rows with `Has_Attachment = False`: {attachment_false}
- Rows with noisy communication text: {body_noise}
- Duplicate ingestion rows: {duplicate_rows}
- Urgent / black-hole requests: {urgent_rows}
- Fee-malformed rows: {fee_rows}

## Notes
The transformation is intentionally designed to be realistic but noisy. It preserves a strong identity-to-record mapping for most rows while introducing a controlled share of conflicting metadata, broken threads, duplicate ingestion, and queue black holes to support downstream analytics and anomaly-detection exercises.
'''

    OUTPUT_SPEC.write_text(spec, encoding="utf-8")


if __name__ == "__main__":
    df = build_dataset()
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    write_spec(df)
    print(f"Created {OUTPUT_CSV} with {len(df)} rows.")
    print(f"Created {OUTPUT_SPEC}.")
