"""
PACS Integration with Critical Result Routing
Bi-directional HL7/DICOM integration for automated critical finding notifications.
Implements critical result communication tracking per ACR guidelines.
"""

import datetime
import json
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class NotificationStatus(Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class EscalationLevel(Enum):
    LEVEL_1_ORDERING = "LEVEL_1_ORDERING_PHYSICIAN"
    LEVEL_2_COVERING = "LEVEL_2_COVERING_PHYSICIAN"
    LEVEL_3_DEPARTMENT_CHIEF = "LEVEL_3_DEPARTMENT_CHIEF"
    LEVEL_4_ADMINISTRATION = "LEVEL_4_ADMINISTRATION"


@dataclass
class CriticalResultNotification:
    """Tracks a critical finding notification through the communication chain."""
    notification_id: str
    case_id: str
    finding_category: str
    severity: str
    finding_summary: str
    ordering_physician: str
    ordering_physician_id: str
    notification_status: str
    escalation_level: str
    attempts: List[Dict[str, Any]]
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[str]
    escalation_deadline_minutes: int
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HL7Message:
    """Represents an HL7 v2.x message for critical result notification."""
    message_type: str
    message_control_id: str
    sending_application: str
    receiving_application: str
    patient_id: str
    patient_name: str
    accession_number: str
    result_status: str
    observation_value: str
    observation_datetime: str

    def to_hl7_string(self) -> str:
        """Generate HL7 v2.5 ORU message string."""
        timestamp = self.observation_datetime.replace("-", "").replace(":", "")[:14]
        return (
            f"MSH|^~\\&|{self.sending_application}|RADFLOW|{self.receiving_application}|PACS|"
            f"{timestamp}||ORU^R01|{self.message_control_id}|P|2.5\r"
            f"PID|||{self.patient_id}||{self.patient_name}\r"
            f"OBR|||{self.accession_number}|CRITICAL_RESULT\r"
            f"OBX|1|ST|FINDING||{self.observation_value}||||||F\r"
            f"OBX|2|ST|STATUS||{self.result_status}||||||F\r"
        )


class PACSCriticalResultRouter:
    """
    Manages critical finding notifications to referring physicians.
    Implements ACR Practice Parameter for Communication of Diagnostic
    Imaging Findings with escalation protocols.
    """

    # ACR-mandated escalation timelines (minutes)
    ESCALATION_TIMELINES = {
        "CRITICAL": 30,      # Critical: 30 min to first attempt
        "URGENT": 120,       # Urgent: 2 hours
        "SIGNIFICANT": 1440, # Significant: 24 hours
    }

    def __init__(self):
        self.notifications: Dict[str, CriticalResultNotification] = {}
        self.escalation_queue: List[str] = []
        self.communication_log: List[Dict[str, Any]] = []

    def create_notification(
        self,
        case_id: str,
        finding_category: str,
        severity: str,
        finding_summary: str,
        ordering_physician: str,
        ordering_physician_id: str,
    ) -> CriticalResultNotification:
        """Create a new critical result notification and initiate routing."""
        notification_id = f"CRN-{uuid.uuid4().hex[:8].upper()}"
        deadline = self.ESCALATION_TIMELINES.get(severity, 1440)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        notification = CriticalResultNotification(
            notification_id=notification_id,
            case_id=case_id,
            finding_category=finding_category,
            severity=severity,
            finding_summary=finding_summary,
            ordering_physician=ordering_physician,
            ordering_physician_id=ordering_physician_id,
            notification_status=NotificationStatus.PENDING.value,
            escalation_level=EscalationLevel.LEVEL_1_ORDERING.value,
            attempts=[],
            acknowledged_by=None,
            acknowledged_at=None,
            escalation_deadline_minutes=deadline,
            created_at=now,
            updated_at=now,
        )

        self.notifications[notification_id] = notification
        self.communication_log.append({
            "event": "NOTIFICATION_CREATED",
            "notification_id": notification_id,
            "severity": severity,
            "timestamp": now,
        })

        return notification

    def attempt_notification(
        self,
        notification_id: str,
        method: str = "PHONE",
        contact_info: str = "",
        reached: bool = False,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Record a notification attempt."""
        if notification_id not in self.notifications:
            return {"error": f"Notification {notification_id} not found"}

        notification = self.notifications[notification_id]
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        attempt = {
            "attempt_number": len(notification.attempts) + 1,
            "method": method,
            "contact_info": contact_info,
            "reached": reached,
            "notes": notes,
            "timestamp": now,
        }
        notification.attempts.append(attempt)
        notification.updated_at = now

        if reached:
            notification.notification_status = NotificationStatus.SENT.value
        elif len(notification.attempts) >= 3:
            # Auto-escalate after 3 failed attempts
            self._escalate_notification(notification_id)

        self.communication_log.append({
            "event": "NOTIFICATION_ATTEMPT",
            "notification_id": notification_id,
            "attempt": attempt,
            "timestamp": now,
        })

        return {"status": "recorded", "attempt": attempt}

    def acknowledge_notification(
        self,
        notification_id: str,
        acknowledged_by: str,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Record acknowledgment of a critical result by the receiving physician."""
        if notification_id not in self.notifications:
            return {"error": f"Notification {notification_id} not found"}

        notification = self.notifications[notification_id]
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        notification.notification_status = NotificationStatus.ACKNOWLEDGED.value
        notification.acknowledged_by = acknowledged_by
        notification.acknowledged_at = now
        notification.updated_at = now

        self.communication_log.append({
            "event": "NOTIFICATION_ACKNOWLEDGED",
            "notification_id": notification_id,
            "acknowledged_by": acknowledged_by,
            "notes": notes,
            "timestamp": now,
        })

        return {"status": "acknowledged", "notification_id": notification_id}

    def _escalate_notification(self, notification_id: str) -> None:
        """Escalate a notification to the next level in the chain."""
        notification = self.notifications[notification_id]
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        escalation_chain = [
            EscalationLevel.LEVEL_1_ORDERING,
            EscalationLevel.LEVEL_2_COVERING,
            EscalationLevel.LEVEL_3_DEPARTMENT_CHIEF,
            EscalationLevel.LEVEL_4_ADMINISTRATION,
        ]

        current_idx = escalation_chain.index(
            EscalationLevel(notification.escalation_level)
        ) if EscalationLevel(notification.escalation_level) in escalation_chain else 0

        if current_idx < len(escalation_chain) - 1:
            next_level = escalation_chain[current_idx + 1]
            notification.escalation_level = next_level.value
            notification.notification_status = NotificationStatus.ESCALATED.value
            notification.updated_at = now

            self.communication_log.append({
                "event": "NOTIFICATION_ESCALATED",
                "notification_id": notification_id,
                "from_level": escalation_chain[current_idx].value,
                "to_level": next_level.value,
                "timestamp": now,
            })

    def generate_hl7_notification(self, notification_id: str, patient_id: str, patient_name: str) -> Optional[str]:
        """Generate HL7 ORU message for a critical result notification."""
        if notification_id not in self.notifications:
            return None

        notification = self.notifications[notification_id]
        msg = HL7Message(
            message_type="ORU^R01",
            message_control_id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
            sending_application="RADFLOW_SENTINEL",
            receiving_application="PACS",
            patient_id=patient_id,
            patient_name=patient_name,
            accession_number=notification.case_id,
            result_status="C" if notification.severity == "CRITICAL" else "F",
            observation_value=notification.finding_summary,
            observation_datetime=notification.created_at,
        )
        return msg.to_hl7_string()

    def get_pending_notifications(self) -> List[Dict[str, Any]]:
        """Get all notifications pending acknowledgment."""
        return [
            n.to_dict() for n in self.notifications.values()
            if n.notification_status in [
                NotificationStatus.PENDING.value,
                NotificationStatus.SENT.value,
                NotificationStatus.ESCALATED.value,
            ]
        ]

    def get_compliance_report(self) -> Dict[str, Any]:
        """Generate ACR compliance report for critical result communications."""
        total = len(self.notifications)
        acknowledged = sum(
            1 for n in self.notifications.values()
            if n.notification_status == NotificationStatus.ACKNOWLEDGED.value
        )
        escalated = sum(
            1 for n in self.notifications.values()
            if n.notification_status == NotificationStatus.ESCALATED.value
        )
        pending = sum(
            1 for n in self.notifications.values()
            if n.notification_status in [
                NotificationStatus.PENDING.value,
                NotificationStatus.SENT.value,
            ]
        )

        # Calculate average acknowledgment time
        ack_times = []
        for n in self.notifications.values():
            if n.acknowledged_at and n.created_at:
                created = datetime.datetime.fromisoformat(n.created_at)
                acked = datetime.datetime.fromisoformat(n.acknowledged_at)
                ack_times.append((acked - created).total_seconds() / 60)

        return {
            "total_notifications": total,
            "acknowledged": acknowledged,
            "escalated": escalated,
            "pending": pending,
            "acknowledgment_rate": acknowledged / max(total, 1),
            "average_acknowledgment_minutes": sum(ack_times) / max(len(ack_times), 1),
            "compliance_status": "COMPLIANT" if pending == 0 and escalated == 0 else "REQUIRES_ATTENTION",
            "report_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
