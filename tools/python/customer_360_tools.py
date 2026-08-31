"""
Customer 360 tools — aggregate customer profile from CRM, CBS, CASA, NRO/NRE accounts.
These are stub implementations; replace with real API calls to your enterprise systems.
"""

from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool
def get_customer_profile(customer_id: str) -> dict:
    """
    Retrieve a unified Customer 360 profile from CRM and Core Banking System.

    :param customer_id: The bank's internal customer identifier.
    :return: A dict containing customerType, kycStatus, accounts, existingExposure and relationshipTenure.
    """
    # Stub — replace with real CRM + CBS API call
    return {
        "customerId": customer_id,
        "customerType": "NRI",
        "name": "Arjun Sharma",
        "kycStatus": "VALID",
        "kycExpiry": "2027-03-01",
        "accounts": ["CASA", "NRO"],
        "existingExposure": 850000,
        "relationshipTenure": 8,
        "segment": "AFFLUENT",
        "rmName": "Priya Mehta",
    }


@tool
def get_account_summary(customer_id: str, account_type: str) -> dict:
    """
    Return balance and transaction summary for a specific account type.

    :param customer_id: The bank's internal customer identifier.
    :param account_type: Account type, e.g. CASA, NRO, NRE.
    :return: A dict containing accountNumber, balance, currency and last12MonthsAvgBalance.
    """
    # Stub
    return {
        "customerId": customer_id,
        "accountType": account_type,
        "accountNumber": "XXXX-1234",
        "balance": 1250000.00,
        "currency": "INR",
        "last12MonthsAvgBalance": 980000.00,
        "status": "ACTIVE",
    }


@tool
def get_existing_loans(customer_id: str) -> list:
    """
    Retrieve all active loan accounts for the customer.

    :param customer_id: The bank's internal customer identifier.
    :return: A list of active loans with loanId, product, outstanding and emi.
    """
    # Stub
    return [
        {
            "loanId": "L-99001",
            "product": "HOME_LOAN",
            "sanctionedAmount": 3000000,
            "outstanding": 2200000,
            "emi": 28000,
            "status": "ACTIVE",
        }
    ]
