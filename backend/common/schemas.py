from typing import Optional
from pydantic import BaseModel, Field


class MedicineRecord(BaseModel):
    medicine_name: str
    active_ingredient: Optional[str] = None
    strength: Optional[str] = None
    dose: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None

    prescription_id: str
    identification_status: str
    identification_confidence: Optional[float] = None


class PrescriptionResult(BaseModel):
    prescription_id: str
    medicines: list[MedicineRecord]


class SafetyFinding(BaseModel):
    finding_type: str
    medicine_a: Optional[str] = None
    medicine_b: Optional[str] = None

    source_a: Optional[str] = None
    source_b: Optional[str] = None

    severity: str
    explanation: str
    evidence_source: Optional[str] = None


class SafetyAnalysisResult(BaseModel):
    analysis_status: str
    findings: list[SafetyFinding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)