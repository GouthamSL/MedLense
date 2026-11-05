# MEDLENSE – Medication Safety Engine

## Project Overview
MEDLENSE is an offline‑first, CPU‑only medication safety platform built for a 24‑hour national‑level healthcare hackathon.  It ingests **prescription data** and **patient‑reported information** (allergies, diseases, symptoms) and produces a set of **SafetyFinding** objects that flag:
- drug‑drug interactions
- duplicate active ingredients
- dosage limit violations
- allergy matches
- disease contraindications
- possible adverse‑effect associations
- temporal symptom‑timeline relationships
- treatment‑response trends

The system never makes diagnostic claims or suggests medication changes; it only surfaces **information‑missing** limitations when evidence is unavailable.

---

## System Architecture
```
backend/
├─ common/                # shared Pydantic schemas
│   └─ schemas.py
├─ medication_safety/     # core safety checkers
│   ├─ evidence_manager.py
│   ├─ interaction_checker.py
│   ├─ duplicate_checker.py
│   ├─ dosage_checker.py
│   ├─ allergy_checker.py
│   ├─ disease_checker.py
│   ├─ adverse_effect_checker.py
│   ├─ symptom_timeline.py
│   ├─ treatment_response.py
│   └─ safety_engine.py
└─ medication_safety/tests/   # unit tests
```
Each checker is a thin, deterministic wrapper around CSV‑based knowledge bases stored in `database/`.

---

## Complete Workflow
1. **Load prescription results** – a `PrescriptionResult` (list of `MedicineRecord`).
2. **Instantiate `MedicationSafetyEngine`** – optionally inject a custom `EvidenceManager` that points at a temporary `database/` for testing.
3. **Run `engine.run(...)`** with optional patient data (`allergies`, `patient_diseases`).
4. The engine returns a `SafetyAnalysisResult` containing:
   - `analysis_status` (`completed` or `no_input`)
   - `findings` – a list of `SafetyFinding`
   - `limitations` – free‑form strings describing missing knowledge sources.
5. **Consume findings** – downstream UI or a future *Patient Guidance Engine* can turn them into patient‑friendly explanations.

---

## Technology Stack
- **Python 3.12**
- **pandas** – CSV loading & filtering
- **pydantic** – data validation & typing
- **RapidFuzz** – optional synonym handling (not used in the current version)
- **unittest** – test runner (no external dependencies needed)

All processing is performed locally; no network access or GPU resources are required.

---

## Existing Medication Safety Modules
| Module | Responsibility |
|--------|-----------------|
| `interaction_checker.py` | Detects known drug‑drug interactions (within and across prescriptions). |
| `duplicate_checker.py` | Finds medicines that share the same active ingredient. |
| `dosage_checker.py` | Validates prescribed dose against max daily/single‑dose limits. |
| `allergy_checker.py` | Matches active ingredients against a user‑provided allergy list. |
| `disease_checker.py` | Applies disease‑contraindication rules from `safety_rules.csv`. |
| `adverse_effect_checker.py` | Looks up possible adverse‑effect associations (optional dataset). |
| `symptom_timeline.py` | Links patient‑reported symptoms to prescription start dates (temporal association). |
| `treatment_response.py` | Evaluates symptom severity trends before/after a prescription start. |
| `safety_engine.py` | Orchestrates all checkers and produces the final analysis result. |

---

## Input & Output Schemas
**`backend/common/schemas.py`** defines the public contracts:
- `MedicineRecord` – details of a single medicine in a prescription.
- `PrescriptionResult` – a prescription ID and a list of `MedicineRecord`s.
- `SafetyFinding` – the core finding type with fields:
  - `finding_type` (e.g., `drug_interaction`, `dosage_issue`)
  - `medicine_a`, `medicine_b` (may be `None`)
  - `source_a`, `source_b` – prescription IDs that generated the finding
  - `severity` (`high`, `requires_review`, `information_missing`…)
  - `explanation` – free‑text description
  - `evidence_source` – optional citation string
- `SafetyAnalysisResult` – aggregates findings and an overall `analysis_status`.

---

## How to Run MEDLENSE
```bash
# Clone the repository (already done in the hackathon environment)
cd MedLense
# Install dependencies (offline – packages are vendored in the .venv)
python -m venv .venv
source .venv/Scripts/activate  # Windows
pip install -r requirements.txt

# Example usage (interactive Python shell)
>>> from backend.common.schemas import PrescriptionResult, MedicineRecord
>>> from backend.medication_safety.safety_engine import MedicationSafetyEngine
>>> presc = PrescriptionResult(
...     prescription_id="RX_1",
...     medicines=[MedicineRecord(medicine_name="Aspirin", active_ingredient="acetylsalicylic acid", strength="500 mg", dose="1", frequency="once daily", duration="5", identification_status="identified", prescription_id="RX_1")]
... )
>>> engine = MedicationSafetyEngine()
>>> result = engine.run([presc])
>>> print(result)
```
All CSV files reside under the `database/` folder.  The engine will gracefully handle missing files by emitting `information_missing` findings.

---

## How to Run the Test Suite
```bash
# From the repository root
python -m unittest discover -v backend/medication_safety/tests
```
The suite includes:
- 11 Phase‑1 tests (interaction, duplicate, dosage, allergy, disease, etc.)
- 8 Phase‑2 adverse‑effect tests
- 4 additional tests added in this round covering symptom‑timeline and treatment‑response edge cases.
All tests run offline and require only the standard library plus pandas/pydantic (already installed).

---

## Current Limitations
- **Adverse‑effect dataset** (`adverse_effects.csv`) is empty in the source repository; the checker therefore never produces findings.
- The engine does **not** perform causal inference – it only reports temporal associations.
- No integration with external knowledge bases (e.g., FDA APIs) – all data is static CSV.
- Patient‑friendly wording is planned for Phase 3 (Patient Guidance Engine).

---

*Prepared for the MEDLENSE hackathon evaluation.*

