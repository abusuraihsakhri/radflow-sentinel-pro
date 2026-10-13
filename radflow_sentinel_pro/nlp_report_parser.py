"""
NLP Report Parser for Radiology Reports
Auto-extracts and classifies critical findings from free-text radiology reports.
Uses rule-based NLP with clinical entity recognition for zero-dependency operation.
"""

import re
import json
import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum


class FindingSeverity(Enum):
    CRITICAL = "CRITICAL"
    URGENT = "URGENT"
    SIGNIFICANT = "SIGNIFICANT"
    INCIDENTAL = "INCIDENTAL"
    NORMAL = "NORMAL"


class FindingCategory(Enum):
    PNEUMOTHORAX = "pneumothorax"
    PULMONARY_EMBOLISM = "pulmonary_embolism"
    INTRACRANIAL_HEMORRHAGE = "intracranial_hemorrhage"
    FRACTURE = "fracture"
    MASS_NODULE = "mass_nodule"
    INFILTRATE = "infiltrate"
    EFFUSION = "effusion"
    AORTIC_DISSECTION = "aortic_dissection"
    BOWEL_OBSTRUCTION = "bowel_obstruction"
    APPENDICITIS = "appendicitis"
    FREE_AIR = "free_air"
    OTHER = "other"


@dataclass
class ExtractedFinding:
    """A single clinical finding extracted from a radiology report."""
    finding_id: str
    category: str
    severity: str
    text_span: str
    anatomical_location: str
    laterality: str
    certainty: str
    recommendation: str
    is_new_vs_prior: str
    confidence_score: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NLPParseResult:
    """Complete NLP parsing result for a radiology report."""
    report_id: str
    modality: str
    body_part: str
    findings: List[Dict[str, Any]]
    critical_findings_count: int
    urgent_findings_count: int
    impression_summary: str
    recommended_actions: List[str]
    parse_confidence: float
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Clinical keyword patterns for finding detection
CRITICAL_PATTERNS = {
    FindingCategory.PNEUMOTHORAX: {
        "keywords": [
            r"pneumothorax", r"ptx", r"tension\s+pneumothorax",
            r"lung\s+collapse", r"air\s+in\s+pleural\s+space"
        ],
        "severity": FindingSeverity.CRITICAL,
        "recommendation": "Immediate clinical evaluation. Consider chest tube placement.",
    },
    FindingCategory.PULMONARY_EMBOLISM: {
        "keywords": [
            r"pulmonary\s+embol[ism]+", r"\bpe\b", r"filling\s+defect",
            r"thrombus\s+in\s+(pulmonary|main|lobar|segmental)",
            r"saddle\s+embolus"
        ],
        "severity": FindingSeverity.CRITICAL,
        "recommendation": "Urgent anticoagulation. CT surgery consult if massive PE.",
    },
    FindingCategory.INTRACRANIAL_HEMORRHAGE: {
        "keywords": [
            r"intracranial\s+hemorrhage", r"\bich\b", r"intracerebral\s+hemorrhage",
            r"subdural\s+hematoma", r"epidural\s+hematoma", r"subarachnoid\s+hemorrhage",
            r"\bsah\b", r"\bsdh\b", r"\bedh\b", r"brain\s+bleed"
        ],
        "severity": FindingSeverity.CRITICAL,
        "recommendation": "STAT neurosurgery consultation. Urgent CT angiography.",
    },
    FindingCategory.AORTIC_DISSECTION: {
        "keywords": [
            r"aortic\s+dissection", r"intimal\s+flap", r"false\s+lumen",
            r"stanford\s+(type\s+)?[AB]", r"debakey"
        ],
        "severity": FindingSeverity.CRITICAL,
        "recommendation": "Emergent vascular surgery consultation. Blood pressure control.",
    },
    FindingCategory.FREE_AIR: {
        "keywords": [
            r"free\s+air", r"pneumoperitoneum", r"perforated\s+viscus",
            r"bowel\s+perforation", r"free\s+intraperitoneal\s+air"
        ],
        "severity": FindingSeverity.CRITICAL,
        "recommendation": "Urgent surgical consultation for possible perforation.",
    },
    FindingCategory.MASS_NODULE: {
        "keywords": [
            r"mass\b", r"nodule", r"lesion", r"neoplasm", r"malignancy",
            r"suspicious\s+(for|mass|nodule|lesion)", r"new\s+(mass|nodule|lesion)"
        ],
        "severity": FindingSeverity.URGENT,
        "recommendation": "Recommend tissue sampling or short-interval follow-up per Fleischner guidelines.",
    },
    FindingCategory.FRACTURE: {
        "keywords": [
            r"fracture", r"break", r"displaced", r"comminuted",
            r"pathologic\s+fracture", r"stress\s+fracture"
        ],
        "severity": FindingSeverity.SIGNIFICANT,
        "recommendation": "Orthopedic evaluation if displaced. Follow-up imaging as indicated.",
    },
    FindingCategory.EFFUSION: {
        "keywords": [
            r"pleural\s+effusion", r"effusion", r"ascites",
            r"fluid\s+collection", r"empyema"
        ],
        "severity": FindingSeverity.SIGNIFICANT,
        "recommendation": "Correlate clinically. Consider thoracentesis if moderate-large.",
    },
}

ANATOMICAL_LOCATIONS = [
    (r"(right|rt\.?)\s+(upper|lower|middle)\s+lobe", "right {0} lobe"),
    (r"(left|lt\.?)\s+(upper|lower)\s+lobe", "left {0} lobe"),
    (r"(right|rt\.?)\s+(lung|hemithorax)", "right lung"),
    (r"(left|lt\.?)\s+(lung|hemithorax)", "left lung"),
    (r"(bilateral|both)\s+(lungs|hemithoraces)", "bilateral lungs"),
    (r"(right|rt\.?)\s+(kidney|renal)", "right kidney"),
    (r"(left|lt\.?)\s+(kidney|renal)", "left kidney"),
    (r"(right|rt\.?)\s+(lobe\s+of\s+)?liver", "right liver"),
    (r"(left|lt\.?)\s+(lobe\s+of\s+)?liver", "left liver"),
    (r"(frontal|parietal|temporal|occipital)\s+(lobe|region)", "{0} region"),
    (r"cerebellum", "cerebellum"),
    (r"brainstem", "brainstem"),
    (r"(cervical|thoracic|lumbar|sacral)\s+spine", "{0} spine"),
    (r"(right|rt\.?)\s+(hip|knee|shoulder|ankle)", "right {0}"),
    (r"(left|lt\.?)\s+(hip|knee|shoulder|ankle)", "left {0}"),
]

LATERALITY_PATTERNS = [
    (r"\bright\b|\brt\.?\b", "right"),
    (r"\bleft\b|\blt\.?\b", "left"),
    (r"\bbilateral\b|\bboth\b", "bilateral"),
]

CERTAINTY_PATTERNS = [
    (r"\bdefinite(ly)?\b|\bconsistent with\b|\bdiagnostic of\b", "definite"),
    (r"\bprobable\b|\blikely\b|\bhigh.suspicion\b", "probable"),
    (r"\bpossible\b|\bcannot exclude\b|\bconsider\b", "possible"),
    (r"\bunlikely\b|\bno evidence\b|\bnormal\b", "unlikely"),
]

NEW_VS_PRIOR_PATTERNS = [
    (r"\bnew\b|\bnewly\b|\bnot\s+previously\b", "new"),
    (r"\bunchanged\b|\bstable\b|\bpersist(s|ent)\b", "unchanged"),
    (r"\bincreased\b|\bgrow(n|ing)\b|\benlarged\b|\bworsened\b", "increased"),
    (r"\bdecreased\b|\bimproved\b|\bresolv(ed|ing)\b|\bresidual\b", "decreased"),
    (r"\bno\s+prior\b|\bno\s+comparison\b", "no_prior"),
]


class NLPReportParser:
    """
    Clinical NLP engine for radiology report parsing.
    Extracts critical findings, anatomical locations, laterality,
    certainty levels, and temporal changes from free-text reports.
    """

    def __init__(self):
        self.finding_counter = 0
        self.parse_history: List[Dict[str, Any]] = []

    @staticmethod
    def _is_negated_mention(text: str, offset: int) -> bool:
        """Suppress explicit local negations; not a comprehensive clinical NLP model."""
        clause = re.split(r"[.;\n]", text[max(0, offset - 90):offset])[-1]
        return bool(re.search(
            r"\b(?:no|without|negative for|absence of|free of|ruled out|"
            r"no evidence of|no findings of)\b(?:\s+\w+){0,5}\s*$",
            clause,
        ))

    def _generate_finding_id(self) -> str:
        self.finding_counter += 1
        return f"FIND-{self.finding_counter:04d}"

    def _extract_anatomical_location(self, text: str) -> str:
        text_lower = text.lower()
        for pattern, template in ANATOMICAL_LOCATIONS:
            match = re.search(pattern, text_lower)
            if match:
                groups = match.groups()
                if groups:
                    return template.format(*groups)
                return template
        return "unspecified"

    def _extract_laterality(self, text: str) -> str:
        text_lower = text.lower()
        for pattern, laterality in LATERALITY_PATTERNS:
            if re.search(pattern, text_lower):
                return laterality
        return "unspecified"

    def _extract_certainty(self, text: str) -> str:
        text_lower = text.lower()
        for pattern, certainty in CERTAINTY_PATTERNS:
            if re.search(pattern, text_lower):
                return certainty
        return "indeterminate"

    def _extract_temporal_status(self, text: str) -> str:
        text_lower = text.lower()
        for pattern, status in NEW_VS_PRIOR_PATTERNS:
            if re.search(pattern, text_lower):
                return status
        return "unspecified"

    def _detect_modality(self, report_text: str) -> str:
        text_lower = report_text.lower()
        modality_keywords = {
            "CT": [r"\bct\b", r"computed\s+tomography", r"cat\s+scan"],
            "MRI": [r"\bmri\b", r"magnetic\s+resonance"],
            "XR": [r"\bx-ray\b", r"\bxr\b", r"radiograph", r"chest\s+pa", r"chest\s+ap"],
            "US": [r"\bultrasound\b", r"\bus\b", r"sonograph"],
            "PET": [r"\bpetscan\b", r"\bpet\b", r"pet/ct"],
            "NM": [r"nuclear\s+medicine", r"\bnm\b", r"scintigraphy"],
        }
        for modality, patterns in modality_keywords.items():
            for p in patterns:
                if re.search(p, text_lower):
                    return modality
        return "UNKNOWN"

    def _detect_body_part(self, report_text: str) -> str:
        text_lower = report_text.lower()
        body_parts = {
            "chest": [r"\bchest\b", r"\bthorax\b", r"\blung\b"],
            "head": [r"\bhead\b", r"\bbrain\b", r"\bcranial\b", r"\bct\s+head\b"],
            "abdomen": [r"\babdomen\b", r"\babdominal\b", r"\bbowel\b"],
            "pelvis": [r"\bpelvis\b", r"\bpelvic\b"],
            "spine": [r"\bspine\b", r"\bvertebr\b", r"\bcervical\b.*\bspine\b"],
            "extremity": [r"\bextremity\b", r"\barm\b", r"\bleg\b", r"\bhip\b", r"\bknee\b"],
            "neck": [r"\bneck\b", r"\bcervical\b(?!.*spine)"],
        }
        for part, patterns in body_parts.items():
            for p in patterns:
                if re.search(p, text_lower):
                    return part
        return "unspecified"

    def parse_report(self, report_text: str, report_id: Optional[str] = None) -> NLPParseResult:
        """
        Parse a free-text radiology report and extract clinical findings.

        Args:
            report_text: The full text of the radiology report
            report_id: Optional identifier for the report

        Returns:
            NLPParseResult with all extracted findings and metadata
        """
        if not report_id:
            report_id = f"RPT-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')}"

        findings = []
        text_lower = report_text.lower()

        for category, config in CRITICAL_PATTERNS.items():
            for keyword_pattern in config["keywords"]:
                matches = list(re.finditer(keyword_pattern, text_lower))
                for match in matches:
                    if self._is_negated_mention(text_lower, match.start()):
                        continue
                    # Get surrounding context (±100 chars)
                    start = max(0, match.start() - 100)
                    end = min(len(report_text), match.end() + 100)
                    context = report_text[start:end].strip()

                    finding = ExtractedFinding(
                        finding_id=self._generate_finding_id(),
                        category=category.value,
                        severity=config["severity"].value,
                        text_span=context,
                        anatomical_location=self._extract_anatomical_location(context),
                        laterality=self._extract_laterality(context),
                        certainty=self._extract_certainty(context),
                        recommendation=config["recommendation"],
                        is_new_vs_prior=self._extract_temporal_status(context),
                        confidence_score=0.85 if config["severity"] == FindingSeverity.CRITICAL else 0.75,
                    )
                    findings.append(finding)
                    break  # One match per category is sufficient

        # Deduplicate by category
        seen_categories = set()
        unique_findings = []
        for f in findings:
            if f.category not in seen_categories:
                seen_categories.add(f.category)
                unique_findings.append(f)

        critical_count = sum(1 for f in unique_findings if f.severity == FindingSeverity.CRITICAL.value)
        urgent_count = sum(1 for f in unique_findings if f.severity == FindingSeverity.URGENT.value)

        # Generate recommended actions
        recommended_actions = []
        if critical_count > 0:
            recommended_actions.append("IMMEDIATE: Notify ordering physician of critical finding(s)")
            recommended_actions.append("Document critical result communication per ACR guidelines")
        if urgent_count > 0:
            recommended_actions.append("URGENT: Ensure follow-up imaging or tissue sampling is ordered")

        # Build impression summary
        if critical_count > 0:
            impression = f"CRITICAL: {critical_count} critical finding(s) detected requiring immediate attention."
        elif urgent_count > 0:
            impression = f"URGENT: {urgent_count} urgent finding(s) requiring timely follow-up."
        elif len(unique_findings) > 0:
            impression = f"NOTABLE: {len(unique_findings)} finding(s) identified for clinical correlation."
        else:
            impression = "No critical or urgent findings detected by automated NLP screening."

        result = NLPParseResult(
            report_id=report_id,
            modality=self._detect_modality(report_text),
            body_part=self._detect_body_part(report_text),
            findings=[f.to_dict() for f in unique_findings],
            critical_findings_count=critical_count,
            urgent_findings_count=urgent_count,
            impression_summary=impression,
            recommended_actions=recommended_actions,
            parse_confidence=0.82,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

        self.parse_history.append(result.to_dict())
        return result

    def get_parse_statistics(self) -> Dict[str, Any]:
        """Return aggregate statistics across all parsed reports."""
        total_reports = len(self.parse_history)
        total_critical = sum(r["critical_findings_count"] for r in self.parse_history)
        total_urgent = sum(r["urgent_findings_count"] for r in self.parse_history)
        return {
            "total_reports_parsed": total_reports,
            "total_critical_findings": total_critical,
            "total_urgent_findings": total_urgent,
            "critical_rate": total_critical / max(total_reports, 1),
            "average_findings_per_report": sum(len(r["findings"]) for r in self.parse_history) / max(total_reports, 1),
        }
