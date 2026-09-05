"""
Automated Pytest for radflow-sentinel-pro Enrichment Modules.
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set required environment variable before importing agents
os.environ.setdefault("AUDIT_SECRET_KEY", "test-audit-secret-key-for-unit-tests-only")

import pytest
from enrichment import (
    EnrichmentIdeasImplementationPlansEngine,
    NaturalEngine,
    PacsEngine,
    IncidentalomaEngine,
    RadiologistEngine,
    RegulatoryEngine,
    ReferringEngine,
    LongitudinalEngine,
    RadflowsentinelproEnrichmentSuite,
    enrichment_suite,
)

def test_enrichment_suite_execution():
    suite = RadflowsentinelproEnrichmentSuite()
    res = suite.execute_all(primary_val=0.5, secondary_val=0.2)
    assert len(res) >= 1
    for k, v in res.items():
        assert v.status in ["OPTIMAL", "WARNING", "CRITICAL_ALERT"]
        assert isinstance(v.recommendations, list)

def test_enrichment_threshold_escalation():
    suite = RadflowsentinelproEnrichmentSuite()
    res = suite.execute_all(primary_val=10.0, secondary_val=5.0)
    for k, v in res.items():
        assert v.status in ["WARNING", "CRITICAL_ALERT"]
        assert len(v.alerts) > 0
