# Annotation Guidelines
## Indonesian Higher Education Admission QA Dataset

---

# 1. Objective

The purpose of annotation is to create high-quality Indonesian factoid question-answer pairs for higher education admission question-answering systems.

---

# 2. Annotation Unit

Each annotation record consists of:
- Context
- Question
- Answer Text
- Answer Start Position
- Category Label

---

# 3. Context Annotation Rules

Annotators must:
- use admission-related contexts only,
- use formal Indonesian language,
- avoid duplicated contexts,
- ensure contextual completeness.

Allowed topics:
- registration
- tuition fee
- scholarship
- study program
- admission schedule
- online learning

---

# 4. Question Construction Rules

Questions must:
- be written in formal Indonesian,
- be factoid-based,
- have explicit answers in the context,
- avoid ambiguity.

Examples:
- Apa syarat pendaftaran BINUS Online?
- Kapan jadwal pendaftaran dibuka?
- Di mana lokasi kampus utama?

---

# 5. Answer Annotation Rules

Answers must:
- appear exactly in the context,
- be concise,
- avoid unnecessary words,
- include exact character start positions.

Example:

Context:
"Pendaftaran dibuka pada bulan Januari."

Question:
"Kapan pendaftaran dibuka?"

Answer:
"bulan Januari"

---

# 6. Factoid Categories

| Category | Description |
|---|---|
| What | Definition/information questions |
| Where | Location questions |
| When | Time/date questions |
| Who | Person/entity questions |
| How many | Quantity questions |

---

# 7. Quality Control

Each annotation must be verified through:
- contextual review,
- answer consistency checking,
- duplicate detection,
- manual validation.

---

# 8. Exclusion Rules

Do not annotate:
- ambiguous questions,
- opinion-based questions,
- incomplete contexts,
- non-admission information,
- slang or mixed-language expressions.

---

# 9. Validation Procedure

Validation steps:
1. Initial annotation
2. Secondary reviewer verification
3. Conflict resolution
4. Final approval

---

# 10. Annotation Format Example

| Context | Question | Answer | Category |
|---|---|---|---|
| BINUS Online menyediakan pembelajaran fleksibel | Apa itu BINUS Online? | pembelajaran fleksibel | What |