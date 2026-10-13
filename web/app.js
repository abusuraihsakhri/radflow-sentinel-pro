"use strict";

// This is an educational browser demonstration, not the Python clinical engine.
const $ = id => document.getElementById(id);
let evaluated = 0;
let critical = 0;
let alertsCount = 0;
let latest = null;

function evaluate(payload) {
  const alerts = [];
  const append = (origin_worker, urgency, summary, technical_details) =>
    alerts.push({origin_worker, urgency, summary, technical_details});
  if (payload.primary_metric > 25) {
    append("InvariantQCWorker", "ELEVATED_RISK", "Primary metric threshold exceeded",
      "The illustrative primary threshold is 25.");
  }
  if (payload.is_critical_flag || payload.secondary_metric > 12) {
    append("SafetyEscalationWorker",
      payload.is_critical_flag ? "CRITICAL_STAT_PANIC" : "ELEVATED_RISK",
      "Safety escalation rule triggered",
      "The critical flag or illustrative secondary threshold (12) was exceeded.");
  }
  if (["DISCORDANT", "ANOMALY", "MUTANT", "VIOLATION", "FAIL", "REJECT"]
      .some(term => payload.status_descriptor.toUpperCase().includes(term))) {
    append("ProtocolConformanceWorker", "ELEVATED_RISK",
      "Discordant descriptor", "A configured keyword was found in the descriptor.");
  }

  const severe = alerts.some(a => a.urgency === "CRITICAL_STAT_PANIC");
  const elevated = alerts.length > 0;
  return {
    mode: "LOCAL_BROWSER_DEMONSTRATION",
    task_id: payload.task_id,
    target_identifier: payload.target_identifier,
    overall_urgency: severe ? "CRITICAL_STAT_PANIC" : elevated ? "ELEVATED_RISK" : "ROUTINE",
    integrity_status: severe ? "RECALIBRATION_REQUIRED" : elevated ? "DISCORDANT_ANOMALY" : "VALIDATED_OPTIMAL",
    total_alerts: alerts.length,
    critical_alerts_count: alerts.filter(a => a.urgency === "CRITICAL_STAT_PANIC").length,
    alerts,
    audit_hash: null,
    audit_note: "Not cryptographically signed. No Python backend was invoked.",
    evaluated_at: new Date().toISOString()
  };
}

function submitAudit(event) {
  event.preventDefault();
  const primary = Number($("primary_metric").value);
  const secondary = Number($("secondary_metric").value);
  if (!Number.isFinite(primary) || !Number.isFinite(secondary)
      || !$("task_id").value.trim() || !$("target_id").value.trim()) {
    $("outputConsole").textContent = "Enter valid identifiers and finite numbers.";
    return;
  }
  const payload = {
    task_id: $("task_id").value.trim(),
    target_identifier: $("target_id").value.trim(),
    primary_metric: primary,
    secondary_metric: secondary,
    status_descriptor: $("status_descriptor").value.trim(),
    is_critical_flag: $("is_critical").checked
  };
  latest = evaluate(payload);
  evaluated += 1;
  critical += Number(latest.critical_alerts_count > 0);
  alertsCount += latest.total_alerts;
  $("m-tasks").textContent = String(evaluated);
  $("m-critical").textContent = String(critical);
  $("m-alerts").textContent = String(alertsCount);
  $("outputConsole").textContent = JSON.stringify(latest, null, 2);
  $("exportBtn").disabled = false;
}

function exportResult() {
  if (!latest) return;
  const blob = new Blob([JSON.stringify(latest, null, 2) + "\n"], {type: "application/json"});
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = "radflow-demonstration.json";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(href), 1000);
}

document.addEventListener("DOMContentLoaded", () => {
  $("auditForm").addEventListener("submit", submitAudit);
  $("exportBtn").addEventListener("click", exportResult);
});
