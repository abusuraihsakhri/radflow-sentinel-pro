"""
FastAPI REST API Server for Radflow Sentinel Pro.
"""
import os
import hmac
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard, SecurityException
from .metrics import GLOBAL_METRICS
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Radflow Sentinel Pro API",
    description="Enterprise Distributed Component Platform (Radiology & Neuroimaging Systems)",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


def require_api_token(authorization: Optional[str] = Header(default=None)) -> None:
    """Fail closed unless an operator configures and supplies a bearer token."""
    expected = os.getenv("API_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="API_TOKEN is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required",
                            headers={"WWW-Authenticate": "Bearer"})
    supplied = authorization[len("Bearer "):]
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid token",
                            headers={"WWW-Authenticate": "Bearer"})


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "radflow-sentinel-pro", "domain": "Radiology & Neuroimaging Systems", "standard": "ACR RADS / Fleischner Society / ASPECTS Guidelines", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics", response_class=PlainTextResponse, dependencies=[Depends(require_api_token)])
def metrics():
    return GLOBAL_METRICS.export_prometheus_text()


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload, _: None = Depends(require_api_token)):
    try:
        dossier = supervisor.process_task(payload)
        return dossier.to_dict()
    except SecurityException:
        raise HTTPException(status_code=400, detail="Sensitive identifier rejected")


@app.post("/api/chat")
def api_chat(req: ChatRequest, _: None = Depends(require_api_token)):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except SecurityException:
        raise HTTPException(status_code=400, detail="Sensitive identifier rejected")


@app.get("/api/audit/logs")
def api_audit_logs(_: None = Depends(require_api_token)):
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
