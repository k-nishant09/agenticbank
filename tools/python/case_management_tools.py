"""
Case management tools — maintain the authoritative case state machine.
The state is stored in a durable case store (not in the LLM context).
This gives the bank a deterministic business state even if an LLM fails.

Valid state transitions:
INTAKE → IDENTITY_VERIFIED → CREDIT_ASSESSMENT → LOAN_ELIGIBLE → COMPLIANCE_CHECK
→ HUMAN_REVIEW (exception path) | APPROVED → FX_QUOTE → CUSTOMER_CONFIRM
→ PAYMENT_READY → AUTHORIZATION → EXECUTED → CLOSED
"""

from ibm_watsonx_orchestrate.agent_builder.tools import tool

VALID_STATES = [
    "INTAKE",
    "IDENTITY_VERIFIED",
    "CREDIT_ASSESSMENT",
    "LOAN_ELIGIBLE",
    "COMPLIANCE_CHECK",
    "EXCEPTION",
    "HUMAN_REVIEW",
    "APPROVED",
    "FX_QUOTE",
    "CUSTOMER_CONFIRM",
    "PAYMENT_READY",
    "AUTHORIZATION",
    "EXECUTED",
    "CLOSED",
    "PENDING_EXTERNAL_SYSTEM",
    "REJECTED",
]


@tool
def create_case(customer_id: str, intent: str, channel: str) -> dict:
    """
    Create a new banking case and return the case ID and initial state.

    :param customer_id: The bank's internal customer identifier.
    :param intent: Customer's expressed intent, e.g. LOAN_PLUS_REMITTANCE.
    :param channel: Originating channel, e.g. MOBILE, INTERNET_BANKING, BRANCH.
    :return: A dict with caseId, state, createdAt and decomposedIntents.
    """
    # Stub — replace with Case Management System API
    return {
        "caseId": "CASE-2026-00441",
        "customerId": customer_id,
        "intent": intent,
        "channel": channel,
        "state": "INTAKE",
        "decomposedIntents": ["PERSONAL_LOAN_7500000", "OVERSEAS_REMITTANCE_2000000_SGP"],
        "createdAt": "2026-07-15T08:45:00Z",
        "assignedRm": "Priya Mehta",
    }


@tool
def advance_case_state(case_id: str, new_state: str, actor: str, remarks: str = "") -> dict:
    """
    Advance the case to the next valid state. Invalid transitions are rejected.
    This enforces the case state machine — the LLM cannot skip required steps.

    :param case_id: The case identifier.
    :param new_state: Target state (must be a valid state from the state machine).
    :param actor: Identifier of the agent, tool or human moving the case.
    :param remarks: Optional remarks for audit log.
    :return: A dict with caseId, previousState, newState and transitionTimestamp.
    """
    if new_state not in VALID_STATES:
        return {"error": f"Invalid state '{new_state}'. Valid states: {VALID_STATES}"}
    # Stub — replace with Case Management System state transition API
    return {
        "caseId": case_id,
        "previousState": "INTAKE",  # retrieved from store in real impl
        "newState": new_state,
        "actor": actor,
        "remarks": remarks,
        "transitionTimestamp": "2026-07-15T09:00:00Z",
    }


@tool
def get_case(case_id: str) -> dict:
    """
    Retrieve the full case record including current state, artifacts and audit trail.

    :param case_id: The case identifier.
    :return: A dict with caseId, state, artifacts (customer360, credit, compliance, etc.) and history.
    """
    # Stub
    return {
        "caseId": case_id,
        "customerId": "C123",
        "state": "COMPLIANCE_CHECK",
        "intent": "LOAN_PLUS_REMITTANCE",
        "artifacts": {
            "customer360": {"customerId": "C123", "customerType": "NRI", "kycStatus": "VALID"},
            "credit": {"creditScore": 781, "eligibilityStatus": "PRELIMINARY_ELIGIBLE"},
            "compliance": None,
        },
        "history": [
            {"state": "INTAKE", "actor": "case_supervisor_agent", "timestamp": "2026-07-15T08:45:00Z"},
            {"state": "IDENTITY_VERIFIED", "actor": "kyc_nri_agent", "timestamp": "2026-07-15T08:50:00Z"},
            {"state": "CREDIT_ASSESSMENT", "actor": "credit_bureau_agent", "timestamp": "2026-07-15T08:55:00Z"},
            {"state": "LOAN_ELIGIBLE", "actor": "credit_assessment_agent", "timestamp": "2026-07-15T09:00:00Z"},
            {"state": "COMPLIANCE_CHECK", "actor": "compliance_supervisor_agent", "timestamp": "2026-07-15T09:05:00Z"},
        ],
        "updatedAt": "2026-07-15T09:05:00Z",
    }


@tool
def add_case_artifact(case_id: str, artifact_type: str, artifact_data: dict) -> dict:
    """
    Attach a named artifact to the case (e.g. customer360, creditReport, amlResult).
    Artifacts are the structured outputs produced by collaborator agents.

    :param case_id: The case identifier.
    :param artifact_type: Artifact name, e.g. customer360, creditReport, amlResult, fxQuote.
    :param artifact_data: The structured artifact data as a dict.
    :return: A dict confirming the artifact was stored.
    """
    # Stub
    return {
        "caseId": case_id,
        "artifactType": artifact_type,
        "stored": True,
        "storedAt": "2026-07-15T09:10:00Z",
    }


@tool
def escalate_to_human(case_id: str, reason: str, escalation_type: str, assigned_queue: str) -> dict:
    """
    Escalate a case to a human reviewer. This is a first-class state, not a failure.
    Used for MEDIUM/HIGH risk decisions, compliance exceptions and credit borderline cases.

    :param case_id: The case identifier.
    :param reason: Reason for escalation (must be specific and traceable).
    :param escalation_type: Type: CREDIT_REVIEW | COMPLIANCE_REVIEW | AUTHORIZATION | EXCEPTION.
    :param assigned_queue: Name of the human review queue to route the case to.
    :return: A dict with escalationId, assignedQueue, slaHours and state.
    """
    # Stub — replace with case management / workflow escalation API
    return {
        "caseId": case_id,
        "escalationId": f"ESC-{case_id}-001",
        "escalationType": escalation_type,
        "reason": reason,
        "assignedQueue": assigned_queue,
        "state": "HUMAN_REVIEW",
        "slaHours": 4,
        "escalatedAt": "2026-07-15T09:15:00Z",
    }
