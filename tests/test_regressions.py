"""Regressions for clinical flags, negated findings, authentication, and guidance."""
import csv
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from radflow_sentinel_pro.csv_utils import parse_csv_bool
from radflow_sentinel_pro.incidentaloma_manager import FleischnerGuidelines, TIRADSGuidelines
from radflow_sentinel_pro.nlp_report_parser import NLPReportParser
from radflow_sentinel_pro.cli import main as clinical_main
from radflow_sentinel_pro.server import create_app
from agents.api import app as supervisor_app
from agents.llm_factory import LLMFactory
from cli import main as supervisor_main


@pytest.mark.parametrize("value,expected", [
    ("False", False), ("0", False), ("no", False), ("", False),
    ("True", True), ("1", True), ("YES", True), (True, True), (False, False)
])
def test_csv_boolean_literals(value, expected):
    assert parse_csv_bool(value) is expected


def test_ambiguous_csv_boolean_rejected():
    with pytest.raises(ValueError):
        parse_csv_bool("possibly")


def test_ground_glass_small_nodule_path():
    result = FleischnerGuidelines.get_recommendation("ground_glass", 5.0)
    assert result["interval_months"] == 0
    assert FleischnerGuidelines.get_recommendation("part_solid", 5.0)["interval_months"] == 0
    low_risk = FleischnerGuidelines.get_recommendation("solid", 7.0, is_high_risk=False)
    high_risk = FleischnerGuidelines.get_recommendation("solid", 7.0, is_high_risk=True)
    assert low_risk["interval_months"] == high_risk["interval_months"] == 6
    assert "18-24" in low_risk["action"]


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_invalid_nodule_dimensions_rejected(value):
    with pytest.raises(ValueError):
        FleischnerGuidelines.get_recommendation("solid", value)
    with pytest.raises(ValueError):
        TIRADSGuidelines.get_recommendation("TR4", value)


def test_radiology_negation_is_not_critical():
    parser = NLPReportParser()
    result = parser.parse_report("CT chest. No evidence of pneumothorax.")
    assert result.critical_findings_count == 0
    result = parser.parse_report("CT chest. No pneumothorax. A pulmonary embolism is present.")
    assert result.critical_findings_count == 1
    assert result.findings[0]["category"] == "pulmonary_embolism"


def test_mock_provider_cannot_claim_external_model():
    with pytest.raises(ValueError):
        LLMFactory.create("openai")
    assert "No clinical analysis" in LLMFactory.create("mock").invoke("system status")


def test_two_csv_entrypoints_treat_false_as_false(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_SECRET_KEY", "test-only-audit-key")
    source = tmp_path / "cases.csv"
    source.write_text(
        "case_id,patient_synthetic_id,metric_primary,metric_secondary,is_stat,status_flag\n"
        "CASE-01,SYNTH-01,10,2,False,NORMAL\n", encoding="utf-8"
    )
    clinical_output = tmp_path / "clinical.csv"
    supervisor_output = tmp_path / "supervisor.csv"
    assert clinical_main(["batch", "-i", str(source), "-o", str(clinical_output)]) == 0
    assert supervisor_main(["batch", "-i", str(source), "-o", str(supervisor_output)]) == 0
    with clinical_output.open(newline="") as stream:
        assert next(csv.DictReader(stream))["overall_status"] == "CONCORDANT_NORMAL"
    with supervisor_output.open(newline="") as stream:
        assert next(csv.DictReader(stream))["overall_urgency"] == "ROUTINE"


def test_invalid_boolean_does_not_write_output(tmp_path):
    source = tmp_path / "invalid.csv"
    source.write_text(
        "case_id,metric_primary,metric_secondary,is_stat\n"
        "CASE-01,10,2,unknown\n", encoding="utf-8"
    )
    output = tmp_path / "out.csv"
    assert clinical_main(["batch", "-i", str(source), "-o", str(output)]) == 2
    assert not output.exists()


def test_supervisory_api_auth_and_prometheus(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "test-only-token")
    monkeypatch.setenv("AUDIT_SECRET_KEY", "test-only-audit-key")
    client = TestClient(supervisor_app)
    payload = {"task_id": "SAFE-1", "target_identifier": "SYNTH-1", "primary_metric": 10}
    assert client.get("/health").status_code == 200
    assert client.post("/api/audit", json=payload).status_code == 401
    assert client.post("/api/audit", json=payload, headers={"Authorization": "Bearer wrong"}).status_code == 401
    headers = {"Authorization": "Bearer test-only-token"}
    assert client.post("/api/audit", json=payload, headers=headers).status_code == 200
    metrics = client.get("/metrics", headers=headers)
    assert metrics.status_code == 200
    assert 'system_tasks_total{system="radflow-sentinel-pro"}' in metrics.text
    assert client.get("/api/audit/logs").status_code == 401


def test_api_missing_token_fails_closed(monkeypatch):
    monkeypatch.delenv("API_TOKEN", raising=False)
    client = TestClient(supervisor_app)
    assert client.get("/api/audit/logs").status_code == 503


def test_clinical_api_requires_token(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "test-only-token")
    app = create_app()
    assert app is not None
    client = TestClient(app)
    assert client.post("/api/chat", json={"query": "status"}).status_code == 401
    assert client.post(
        "/api/chat",
        json={"query": "status"},
        headers={"Authorization": "Bearer test-only-token"},
    ).status_code == 200
