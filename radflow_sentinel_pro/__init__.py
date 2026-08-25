"""
RadFlow Sentinel Pro: Autonomous Radiology Critical Finding Escalation & Incidentaloma Agent
Surveils PACS/RIS narratives for emergency critical findings (PTX, PE, ICH) and schedules Fleischner 2017 & TI-RADS longitudinal follow-ups.
"""
__version__ = "2.0.0-PRO"

try:
    import sys
    import importlib.util
    from pathlib import Path
    _root_file = Path(__file__).parent.parent / "radflow_sentinel_pro.py"
    if _root_file.exists():
        _spec = importlib.util.spec_from_file_location("_radflow_sentinel_pro_root", str(_root_file))
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        AcuteCriticalFinderAgent = getattr(_mod, "AcuteCriticalFinderAgent", None)
        IncidentalomaTrackerAgent = getattr(_mod, "IncidentalomaTrackerAgent", None)
        ContrastSafetyAuditorAgent = getattr(_mod, "ContrastSafetyAuditorAgent", None)
        SentinelCoordinatorPro = getattr(_mod, "SentinelCoordinatorPro", None)
        DomainKnowledgeRegistry = getattr(_mod, "DomainKnowledgeRegistry", None)
        main = getattr(_mod, "main", None)
except Exception:
    pass
