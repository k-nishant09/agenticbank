"""
Credit Bureau tools — retrieve CIBIL score, credit history and liability profile.
READ-ONLY access to bureau. The agent does NOT make the credit decision; it only retrieves data.
"""

from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool
def get_credit_score(customer_id: str, pan_number: str) -> dict:
    """
    Fetch the customer's CIBIL credit score and key bureau attributes.

    :param customer_id: The bank's internal customer identifier.
    :param pan_number: The customer's PAN, used as the bureau lookup key.
    :return: A dict with creditScore, existingEMI, creditStatus, bureauTimestamp and bureauReference.
    """
    # Stub — replace with CIBIL / TransUnion API call
    return {
        "customerId": customer_id,
        "panNumber": pan_number,
        "creditScore": 781,
        "creditRating": "EXCELLENT",
        "existingEMI": 42000,
        "totalExposure": 2200000,
        "creditStatus": "PASS",
        "numberOfActiveAccounts": 3,
        "numberOfEnquiriesLast6Months": 1,
        "dpd30Plus": 0,
        "dpd90Plus": 0,
        "bureauTimestamp": "2026-07-15T08:30:00Z",
        "bureauReference": "CIBIL-2026-789456",
        "source": "CIBIL",
    }


@tool
def get_credit_history(customer_id: str, pan_number: str, months: int = 24) -> dict:
    """
    Retrieve the detailed credit history for the last N months.

    :param customer_id: The bank's internal customer identifier.
    :param pan_number: The customer's PAN.
    :param months: Number of months of history to retrieve (default 24).
    :return: A dict with accountHistory, paymentHistory and enquiries.
    """
    # Stub
    return {
        "customerId": customer_id,
        "periodMonths": months,
        "accountHistory": [
            {"type": "HOME_LOAN", "bank": "AXIS", "sanctioned": 3000000, "outstanding": 2200000, "status": "STANDARD"},
        ],
        "paymentHistory": {"onTime": 96, "late30Days": 0, "late60Days": 0, "late90Days": 0},
        "enquiries": [
            {"date": "2026-06-01", "institution": "AXIS BANK", "purpose": "PERSONAL_LOAN"}
        ],
        "writeOffs": 0,
        "settlements": 0,
    }
