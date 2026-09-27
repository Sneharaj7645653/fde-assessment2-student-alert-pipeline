# Indonesian Higher Education Admission Question-Answering Dataset

## Description

This repository contains an Indonesian factoid-based question-answering dataset designed for higher education admission services. The dataset supports research in Natural Language Processing (NLP), Question Answering (QA), Conversational AI, and transformer-based language models such as IndoBERT.

The dataset was developed from admission-related resources including institutional admission websites, admission brochures, and historical admission inquiries from prospective students.

---

# Dataset Characteristics

- Language: Indonesian (formal language)
- Domain: Higher Education Admission
- Question Type: Factoid
- QA Type: Closed-domain Question Answering
- Format: Parquet, CSV, JSON
- Annotation Type: Context-Question-Answer Span

---

# Dataset Structure

Each dataset record contains:

| Column | Description |
|---|---|
| context | Admission-related context paragraph |
| question | Question asked by candidate/student |
| answer_text | Ground-truth answer |
| answer_start | Character start index of answer |
| category | Factoid question category |

---

# Factoid Categories

The dataset includes several factoid categories:

- What
- Where
- When
- Who
- How many
- How long
- Quantitative questions

---

# Repository Contents

| File | Description |
|---|---|
| train.parquet | Training dataset |
| validation.parquet | Validation dataset |
| test.parquet | Testing dataset |
| annotation_guidelines.pdf | Annotation guideline document |
| preprocessing_script.py | Data preprocessing script |
| README.md | Repository documentation |

---

# Data Collection

Data were collected from:
- Higher education admission websites
- Admission brochures
- Institutional admission documents
- Historical candidate admission inquiries

---

# Annotation Process

The dataset was manually annotated using Conversational Document Question Answering (CDQA) annotation procedures.

Annotation stages:
1. Context extraction
2. Question generation
3. Answer span selection
4. Factoid category labeling
5. Manual validation

---

# Data Validation

Validation procedures included:
- duplicate removal,
- normalization,
- answer consistency checking,
- contextual verification,
- manual review.

---

# Intended Use

The dataset may be used for:
- Question-answering systems
- Conversational AI
- Educational chatbots
- Transformer fine-tuning
- IndoBERT benchmarking
- Information retrieval research

---

# Limitations

The dataset:
- uses formal Indonesian language,
- does not support slang or dialects,
- focuses only on higher education admission domains,
- contains closed-domain factoid questions.

---

# Citation

If you use this dataset, please cite:

Yossy, E.H., Budiharto, W., Trisetyarso, A., & Suhartono, D. (2025). Indonesian Higher Education Admission Question-Answering Dataset. Mendeley Data.

---

# License

CC BY 4.0