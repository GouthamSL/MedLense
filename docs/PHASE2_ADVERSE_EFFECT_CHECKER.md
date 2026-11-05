# Phase 2 – Adverse‑Effect Checker

## Purpose
The **Adverse‑Effect Checker** evaluates patient‑reported symptoms against a curated CSV dataset (`database/adverse_effects.csv`).
It reports possible adverse‑effect associations **without** inferring causation, recommending a pharmacist/doctor review.

## Dataset (`adverse_effects.csv`)
| Column | Description |
|--------|-------------|
| `active_ingredient` | The exact active ingredient name (e.g. `penicillin`). |
| `symptom` | Symptom name as documented in the source (e.g. `rash`). |
| `severity` | Clinical severity classification (e.g. `high`, `moderate`, `low`). |
| `frequency` | How frequently the effect occurs (may be blank). |
| `evidence_source` | Source of the clinical information (e.g. `FDA`). |
| `reference_url` | URL to the official label or guideline. |
| `verified_date` | Date the record was verified (ISO YYYY‑MM‑DD). |
| `notes` | Optional free‑form notes. |
| `explanation` | Human‑readable explanation of the association (optional, used in findings). |

*The repository ships only a header‑only file* – no verified clinical rows are provided. Real data can be added later by populating the CSV with rows that follow the column definitions.

## Matching logic
1. **Normalisation** – both active ingredient and symptom strings are lower‑cased and stripped of surrounding whitespace.
2. **Exact match only** – the checker does **not** perform fuzzy matching or synonym expansion. A match occurs only when the normalised ingredient **and** symptom equal a row in the CSV.
3. If the dataset is missing or empty, the checker records a finding with `severity="information_missing"` to indicate the limitation.
4. If a medicine lacks an active ingredient (or the ingredient cannot be resolved via the drug catalog), a limitation finding is emitted.
5. If a symptom record lacks a name, a limitation finding is emitted.

## Output (`SafetyFinding`)
* `finding_type = "possible_adverse_effect"`
* `medicine_a` – the medicine name.
* `source_a` – the prescription ID.
* `severity` – from the CSV (`high`, `moderate`, …) or `information_missing` when unavailable.
* `explanation` – taken from the CSV `explanation` column when present; otherwise a generic message.
* `evidence_source` – the CSV `evidence_source` column (may be `None`).

## Safety guarantees
* **No causation** is claimed – the wording makes clear this is a possible association.
* **No treatment changes** are recommended.
* **No invented data** – if the CSV is empty or missing, the checker only reports the limitation.

## Usage example
```python
from backend.medication_safety.adverse_effect_checker import AdverseEffectChecker
from backend.common.schemas import PrescriptionResult, MedicineRecord
from backend.medication_safety.symptom_timeline import SymptomRecord

presc = PrescriptionResult(
    prescription_id="RX_1",
    medicines=[MedicineRecord(medicine_name="Penicillin", active_ingredient="penicillin",
                              prescription_id="RX_1", identification_status="identified")],
)

symptoms = [SymptomRecord(symptom_name="rash", onset=datetime.now())]

checker = AdverseEffectChecker()
findings = checker.check([presc], symptoms)
print(findings)
```
If `adverse_effects.csv` contains a matching row, the finding will include the severity and evidence source; otherwise a limitation finding is returned.

## Running the tests
```bash
python -m pytest backend/medication_safety/tests -v
```
The test suite includes the original 11 Phase 1 tests and the 8 new Phase 2 tests, for a total of **19** passing tests.

---
**Note:** The current repository ships a header‑only `adverse_effects.csv`. To add verified clinical data, simply append rows that follow the column definitions above.

