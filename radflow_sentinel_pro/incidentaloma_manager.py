"""
Incidentaloma Management Pathway Automation
Auto-schedules follow-up imaging based on Fleischner Society 2017 and TI-RADS guidelines.
Manages the complete lifecycle of incidental findings from detection to resolution.
"""

import datetime
import math
import uuid
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class IncidentalomaType(Enum):
    PULMONARY_NODULE = "pulmonary_nodule"
    THYROID_NODULE = "thyroid_nodule"
    ADRENAL_NODULE = "adrenal_nodule"
    RENAL_CYST = "renal_cyst"
    HEPATIC_LESION = "hepatic_lesion"
    PANCREATIC_CYST = "pancreatic_cyst"
    LYMPHADENOPATHY = "lymphadenopathy"
    OTHER = "other"


class FollowUpStatus(Enum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"
    RESOLVED = "RESOLVED"


class RiskLevel(Enum):
    LOW = "LOW"
    INTERMEDIATE = "INTERMEDIATE"
    HIGH = "HIGH"


@dataclass
class FollowUpRecommendation:
    """A recommended follow-up action for an incidentaloma."""
    recommendation_id: str
    incidentaloma_type: str
    finding_description: str
    risk_level: str
    recommended_interval_months: int
    recommended_modality: str
    guideline_source: str
    rationale: str
    follow_up_status: str
    scheduled_date: Optional[str]
    completed_date: Optional[str]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IncidentalomaRecord:
    """Complete record of an incidentaloma and its management pathway."""
    record_id: str
    patient_ref: str
    incidentaloma_type: str
    finding_description: str
    size_mm: float
    location: str
    initial_detection_date: str
    risk_level: str
    follow_ups: List[Dict[str, Any]]
    current_status: str
    resolution_date: Optional[str]
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FleischnerGuidelines:
    """
    Implements Fleischner Society 2017 Guidelines for pulmonary nodule management.
    Supports both solid and subsolid nodule categories.
    """

    SOLID_NODULE_LOW_RISK = {
        "<6mm": {"interval_months": 0, "action": "No follow-up required", "modality": "N/A"},
        "6-8mm": {"interval_months": 12, "action": "Optional CT at 12 months", "modality": "CT Chest"},
        ">8mm": {"interval_months": 3, "action": "CT at 3 months, consider PET/CT or tissue sampling", "modality": "CT Chest"},
    }

    SOLID_NODULE_HIGH_RISK = {
        "<6mm": {"interval_months": 12, "action": "Optional CT at 12 months", "modality": "CT Chest"},
        "6-8mm": {"interval_months": 6, "action": "CT at 6-12 months, consider CT at 18-24 months", "modality": "CT Chest"},
        ">8mm": {"interval_months": 3, "action": "CT at 3 months, PET/CT, or tissue sampling", "modality": "CT/PET-CT"},
    }

    SUBSOLID_NODULES = {
        "ground_glass_<6mm": {"interval_months": 0, "action": "No routine follow-up", "modality": "N/A"},
        "ground_glass_>=6mm": {"interval_months": 6, "action": "CT at 6-12 months, then every 2 years for 5 years", "modality": "CT Chest"},
        "part_solid": {"interval_months": 3, "action": "CT at 3-6 months, then annually for 5 years", "modality": "CT Chest"},
    }

    @classmethod
    def get_recommendation(
        cls,
        nodule_type: str,
        size_mm: float,
        is_high_risk: bool = False,
    ) -> Dict[str, Any]:
        """Get Fleischner guideline recommendation for a pulmonary nodule."""
        if size_mm < 0 or not math.isfinite(size_mm):
            raise ValueError("size_mm must be a finite, non-negative measurement")
        if nodule_type == "solid":
            table = cls.SOLID_NODULE_HIGH_RISK if is_high_risk else cls.SOLID_NODULE_LOW_RISK
            if size_mm < 6:
                return table["<6mm"]
            elif size_mm <= 8:
                return table["6-8mm"]
            else:
                return table[">8mm"]
        elif nodule_type == "ground_glass":
            if size_mm < 6:
                return cls.SUBSOLID_NODULES["ground_glass_<6mm"]
            else:
                return cls.SUBSOLID_NODULES["ground_glass_>=6mm"]
        elif nodule_type == "part_solid":
            return cls.SUBSOLID_NODULES["part_solid"]
        return {"interval_months": 0, "action": "Clinical correlation recommended", "modality": "N/A"}


class TIRADSGuidelines:
    """
    Implements ACR TI-RADS 2017 guidelines for thyroid nodule management.
    """

    TI_RADS_COMPOSITION = {
        "cystic": 0, "spongiform": 0, "mixed": 1, "solid": 2,
    }
    TI_RADS_ECHOGENICITY = {
        "anechoic": 0, "hyperechoic": 1, "isoechoic": 1, "hypoechoic": 2, "very_hypoechoic": 3,
    }
    TI_RADS_SHAPE = {
        "wider_than_tall": 0, "taller_than_wider": 3,
    }
    TI_RADS_MARGIN = {
        "smooth": 0, "ill_defined": 0, "lobulated": 2, "extra_thyroidal": 3,
    }
    TI_RADS_ECHOGENIC_FOCI = {
        "none": 0, "large": 1, "peripheral": 2, "punctate": 3,
    }

    @classmethod
    def calculate_score(cls, composition: str, echogenicity: str, shape: str,
                        margin: str, echogenic_foci: str) -> int:
        """Calculate TI-RADS total score."""
        return (
            cls.TI_RADS_COMPOSITION.get(composition, 0) +
            cls.TI_RADS_ECHOGENICITY.get(echogenicity, 0) +
            cls.TI_RADS_SHAPE.get(shape, 0) +
            cls.TI_RADS_MARGIN.get(margin, 0) +
            cls.TI_RADS_ECHOGENIC_FOCI.get(echogenic_foci, 0)
        )

    @classmethod
    def get_category(cls, score: int) -> str:
        """Map TI-RADS score to category."""
        if score == 0:
            return "TR1"
        elif score <= 2:
            return "TR2"
        elif score == 3:
            return "TR3"
        elif score >= 4 and score <= 6:
            return "TR4"
        else:
            return "TR5"

    @classmethod
    def get_recommendation(cls, category: str, size_mm: float) -> Dict[str, Any]:
        """Get TI-RADS recommendation based on category and size."""
        recommendations = {
            "TR1": {"action": "No FNA or follow-up", "interval_months": 0},
            "TR2": {"action": "No FNA or follow-up", "interval_months": 0},
            "TR3": {"action": "FNA if ≥25mm, follow-up if ≥15mm", "interval_months": 12},
            "TR4": {"action": "FNA if ≥15mm, follow-up if ≥10mm", "interval_months": 12},
            "TR5": {"action": "FNA if ≥10mm, follow-up if ≥5mm", "interval_months": 12},
        }
        rec = recommendations.get(category, {"action": "Clinical correlation", "interval_months": 0}).copy()

        if size_mm < 0 or not math.isfinite(size_mm):
            raise ValueError("size_mm must be a finite, non-negative measurement")

        # Size-based FNA thresholds
        fna_thresholds = {"TR1": 999, "TR2": 999, "TR3": 25, "TR4": 15, "TR5": 10}
        followup_thresholds = {"TR1": 999, "TR2": 999, "TR3": 15, "TR4": 10, "TR5": 5}

        if size_mm >= fna_thresholds.get(category, 999):
            rec["action"] = f"FNA recommended (size {size_mm}mm ≥ threshold)"
        elif size_mm >= followup_thresholds.get(category, 999):
            rec["action"] = f"Follow-up ultrasound recommended (size {size_mm}mm)"

        return rec


class IncidentalomaManager:
    """
    Manages the complete lifecycle of incidental findings.
    Integrates Fleischner and TI-RADS guidelines for automated follow-up scheduling.
    """

    def __init__(self):
        self.records: Dict[str, IncidentalomaRecord] = {}
        self.alert_queue: List[Dict[str, Any]] = []

    def register_incidentaloma(
        self,
        patient_ref: str,
        incidentaloma_type: str,
        finding_description: str,
        size_mm: float,
        location: str,
        detection_date: Optional[str] = None,
        is_high_risk: bool = False,
        **kwargs,
    ) -> IncidentalomaRecord:
        """Register a new incidentaloma and generate follow-up recommendations."""
        record_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        now = detection_date or datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Determine guideline-based recommendation
        if incidentaloma_type == IncidentalomaType.PULMONARY_NODULE.value:
            nodule_type = kwargs.get("nodule_type", "solid")
            rec = FleischnerGuidelines.get_recommendation(nodule_type, size_mm, is_high_risk)
            risk_level = RiskLevel.HIGH.value if is_high_risk and size_mm > 8 else RiskLevel.LOW.value
            guideline = "Fleischner Society 2017"
        elif incidentaloma_type == IncidentalomaType.THYROID_NODULE.value:
            score = TIRADSGuidelines.calculate_score(
                kwargs.get("composition", "solid"),
                kwargs.get("echogenicity", "isoechoic"),
                kwargs.get("shape", "wider_than_tall"),
                kwargs.get("margin", "smooth"),
                kwargs.get("echogenic_foci", "none"),
            )
            category = TIRADSGuidelines.get_category(score)
            rec = TIRADSGuidelines.get_recommendation(category, size_mm)
            risk_level = RiskLevel.HIGH.value if score >= 4 else RiskLevel.LOW.value
            guideline = f"ACR TI-RADS 2017 (Score: {score}, Category: {category})"
        else:
            rec = {"interval_months": 6, "action": "Clinical correlation and short-interval follow-up", "modality": "Appropriate imaging"}
            risk_level = RiskLevel.INTERMEDIATE.value
            guideline = "Clinical judgment"

        follow_up = FollowUpRecommendation(
            recommendation_id=f"FU-{uuid.uuid4().hex[:6].upper()}",
            incidentaloma_type=incidentaloma_type,
            finding_description=finding_description,
            risk_level=risk_level,
            recommended_interval_months=rec.get("interval_months", 0),
            recommended_modality=rec.get("modality", "N/A"),
            guideline_source=guideline,
            rationale=rec.get("action", "Clinical correlation"),
            follow_up_status=FollowUpStatus.SCHEDULED.value if rec.get("interval_months", 0) > 0 else FollowUpStatus.RESOLVED.value,
            scheduled_date=(
                (datetime.datetime.fromisoformat(now) + datetime.timedelta(days=30 * rec.get("interval_months", 0))).isoformat()
                if rec.get("interval_months", 0) > 0 else None
            ),
            completed_date=None,
            created_at=now,
        )

        record = IncidentalomaRecord(
            record_id=record_id,
            patient_ref=patient_ref,
            incidentaloma_type=incidentaloma_type,
            finding_description=finding_description,
            size_mm=size_mm,
            location=location,
            initial_detection_date=now,
            risk_level=risk_level,
            follow_ups=[follow_up.to_dict()],
            current_status="ACTIVE",
            resolution_date=None,
            notes=[f"Registered per {guideline}. {rec.get('action', '')}"],
        )

        self.records[record_id] = record
        return record

    def complete_follow_up(self, record_id: str, follow_up_id: str, new_size_mm: Optional[float] = None) -> Dict[str, Any]:
        """Mark a follow-up as completed and optionally register new findings."""
        if record_id not in self.records:
            return {"error": f"Record {record_id} not found"}

        record = self.records[record_id]
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for fu in record.follow_ups:
            if fu["recommendation_id"] == follow_up_id:
                fu["follow_up_status"] = FollowUpStatus.COMPLETED.value
                fu["completed_date"] = now
                break

        # If size changed, generate new follow-up
        if new_size_mm and new_size_mm != record.size_mm:
            size_change = new_size_mm - record.size_mm
            record.notes.append(
                f"Size change: {record.size_mm}mm → {new_size_mm}mm (Δ{size_change:+.1f}mm)"
            )
            record.size_mm = new_size_mm

            if size_change > 0:
                record.notes.append("Interval growth detected. Upgrading follow-up intensity.")

        return {"status": "completed", "record": record.to_dict()}

    def get_overdue_follow_ups(self) -> List[Dict[str, Any]]:
        """Get all overdue follow-up recommendations."""
        now = datetime.datetime.now(datetime.timezone.utc)
        overdue = []

        for record in self.records.values():
            if record.current_status != "ACTIVE":
                continue
            for fu in record.follow_ups:
                if fu["follow_up_status"] == FollowUpStatus.SCHEDULED.value and fu.get("scheduled_date"):
                    scheduled = datetime.datetime.fromisoformat(fu["scheduled_date"])
                    if now > scheduled:
                        overdue.append({
                            "record_id": record.record_id,
                            "patient_ref": record.patient_ref,
                            "finding": record.finding_description,
                            "scheduled_date": fu["scheduled_date"],
                            "days_overdue": (now - scheduled).days,
                            "modality": fu["recommended_modality"],
                        })

        return sorted(overdue, key=lambda x: x["days_overdue"], reverse=True)

    def get_management_summary(self) -> Dict[str, Any]:
        """Generate summary of all managed incidentalomas."""
        total = len(self.records)
        active = sum(1 for r in self.records.values() if r.current_status == "ACTIVE")
        resolved = sum(1 for r in self.records.values() if r.current_status == "RESOLVED")
        overdue = len(self.get_overdue_follow_ups())

        type_counts = {}
        for r in self.records.values():
            type_counts[r.incidentaloma_type] = type_counts.get(r.incidentaloma_type, 0) + 1

        return {
            "total_incidentalomas": total,
            "active": active,
            "resolved": resolved,
            "overdue_follow_ups": overdue,
            "by_type": type_counts,
            "compliance_rate": (total - overdue) / max(total, 1),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
