"""
KYC / Identity / NRI tools — verify PAN, KYC status, NRI classification and account ownership.
READ-ONLY tools; no write access to identity systems.
"""

from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool
def get_kyc_status(customer_id: str) -> dict:
    """
    Retrieve the current KYC status for a customer.

    :param customer_id: The bank's internal customer identifier.
    :return: A dict with kycStatus (VALID | EXPIRED | PENDING), kycType and expiry date.
    """
    # Stub — replace with KYC system API call
    return {
        "customerId": customer_id,
        "kycStatus": "VALID",
        "kycType": "DIGITAL",
        "verifiedDate": "2024-01-15",
        "expiryDate": "2027-01-15",
        "verificationMode": "CKYC",
    }


@tool
def verify_pan(customer_id: str, pan_number: str) -> dict:
    """
    Verify PAN against the Income Tax Department records and match with customer profile.

    :param customer_id: The bank's internal customer identifier.
    :param pan_number: The customer's PAN (Permanent Account Number).
    :return: A dict with isValid, nameMatch and panStatus.
    """
    # Stub
    return {
        "customerId": customer_id,
        "panNumber": pan_number,
        "isValid": True,
        "nameMatch": True,
        "panStatus": "ACTIVE",
        "linkedAadhaar": True,
    }


@tool
def get_nri_status(customer_id: str) -> dict:
    """
    Determine the customer's NRI/resident classification and applicable account types.

    :param customer_id: The bank's internal customer identifier.
    :return: A dict with residencyStatus, nriType, countryOfResidence and eligibleAccountTypes.
    """
    # Stub
    return {
        "customerId": customer_id,
        "residencyStatus": "NRI",
        "nriType": "NRI_SINGAPORE",
        "countryOfResidence": "SGP",
        "visaType": "EMPLOYMENT",
        "eligibleAccountTypes": ["NRE", "NRO", "FCNR"],
        "femaCategory": "NRI",
    }


@tool
def get_customer_identity(customer_id: str) -> dict:
    """
    Retrieve verified identity documents on record for the customer.

    :param customer_id: The bank's internal customer identifier.
    :return: A dict listing submitted and verified identity documents.
    """
    # Stub
    return {
        "customerId": customer_id,
        "documents": [
            {"type": "PASSPORT", "number": "ZXXXX123", "status": "VERIFIED", "expiry": "2029-06-30"},
            {"type": "PAN", "number": "ABCDE1234F", "status": "VERIFIED"},
            {"type": "AADHAAR", "masked": "XXXX-XXXX-1234", "status": "VERIFIED"},
        ],
        "faceMatch": "PASSED",
        "liveness": "PASSED",
    }
