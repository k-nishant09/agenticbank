"""
Compliance tools — AML, Sanctions, FEMA/Remittance screening.
IMPORTANT: These tools call authoritative compliance systems.
The agent NEVER overrides or bypasses a compliance result.
Any REVIEW_REQUIRED or MATCH result must be routed to a human compliance officer.
"""

from ibm_watsonx_orchestrate.agent_builder.tools import tool


# ─── AML ──────────────────────────────────────────────────────────────────────

@tool
def run_aml_check(
    customer_id: str,
    transaction_amount: float,
    transaction_currency: str,
    transaction_purpose: str,
    beneficiary_id: str,
    destination_country: str,
) -> dict:
    """
    Run a full AML (Anti-Money Laundering) check for a proposed transaction.
    Returns PASS, REVIEW_REQUIRED or REJECT. NEVER infer a result — call this tool.

    :param customer_id: The bank's internal customer identifier.
    :param transaction_amount: Proposed transaction amount.
    :param transaction_currency: ISO 4217 currency code, e.g. INR, SGD.
    :param transaction_purpose: Purpose code or description of the transaction.
    :param beneficiary_id: Beneficiary identifier or account number.
    :param destination_country: ISO 3166-1 alpha-3 destination country code.
    :return: A dict with amlStatus, riskScore, riskCategory and caseReference.
    """
    # Stub — replace with bank's AML engine API (e.g. NICE Actimize, SAS AML)
    return {
        "customerId": customer_id,
        "transactionAmount": transaction_amount,
        "currency": transaction_currency,
        "destinationCountry": destination_country,
        "amlStatus": "PASS",
        "riskScore": 18,
        "riskCategory": "LOW",
        "typologyMatches": [],
        "caseReference": "AML-2026-001234",
        "screenedAt": "2026-07-15T09:00:00Z",
    }


@tool
def get_customer_risk_score(customer_id: str) -> dict:
    """
    Retrieve the current AML risk score and risk category for a customer.

    :param customer_id: The bank's internal customer identifier.
    :return: A dict with riskScore, riskCategory and lastReviewDate.
    """
    # Stub
    return {
        "customerId": customer_id,
        "riskScore": 22,
        "riskCategory": "LOW",
        "lastReviewDate": "2026-01-10",
        "nextReviewDate": "2027-01-10",
        "pep": False,
        "adverseMedia": False,
    }


# ─── SANCTIONS ────────────────────────────────────────────────────────────────

@tool
def screen_sanctions(
    customer_id: str,
    beneficiary_name: str,
    beneficiary_country: str,
    transaction_amount: float,
) -> dict:
    """
    Screen the customer and beneficiary against OFAC, UN, EU and Indian sanctions lists.
    If sanctionStatus is POTENTIAL_MATCH or CONFIRMED_MATCH, the case MUST be stopped
    and escalated to a human compliance officer. Do NOT proceed with the transaction.

    :param customer_id: The bank's internal customer identifier.
    :param beneficiary_name: Full legal name of the beneficiary.
    :param beneficiary_country: ISO 3166-1 alpha-3 beneficiary country code.
    :param transaction_amount: Proposed transaction amount in originating currency.
    :return: A dict with sanctionStatus, matchDetails and caseReference.
    """
    # Stub — replace with sanctions screening service (e.g. Dow Jones, Refinitiv WorldCheck)
    return {
        "customerId": customer_id,
        "beneficiaryName": beneficiary_name,
        "beneficiaryCountry": beneficiary_country,
        "sanctionStatus": "CLEAR",
        "listsChecked": ["OFAC_SDN", "UN_CONSOLIDATED", "EU_CONSOLIDATED", "MHA_INDIA"],
        "matchDetails": [],
        "caseReference": "SANC-2026-005678",
        "screenedAt": "2026-07-15T09:01:00Z",
    }


# ─── FEMA / REMITTANCE ────────────────────────────────────────────────────────

@tool
def check_fema_eligibility(
    customer_id: str,
    remittance_amount_inr: float,
    destination_country: str,
    purpose_code: str,
    account_type: str,
) -> dict:
    """
    Validate a proposed overseas remittance against FEMA (Foreign Exchange Management Act) rules,
    the Liberalised Remittance Scheme (LRS) annual limit and bank policy.

    :param customer_id: The bank's internal customer identifier.
    :param remittance_amount_inr: Remittance amount in INR.
    :param destination_country: ISO 3166-1 alpha-3 destination country code.
    :param purpose_code: RBI purpose code (e.g. P0001 for family maintenance).
    :param account_type: Source account type (e.g. NRO, NRE, CASA).
    :return: A dict with femaStatus, lrsUtilised, lrsRemaining, approvalRequired and remarks.
    """
    # Stub — replace with FEMA/LRS tracking system API
    lrs_annual_limit = 25000000  # USD 250,000 equivalent in INR approx
    lrs_utilised_ytd = 5000000
    lrs_remaining = lrs_annual_limit - lrs_utilised_ytd

    eligible = remittance_amount_inr <= lrs_remaining

    return {
        "customerId": customer_id,
        "remittanceAmountINR": remittance_amount_inr,
        "destinationCountry": destination_country,
        "purposeCode": purpose_code,
        "accountType": account_type,
        "femaStatus": "ELIGIBLE" if eligible else "LIMIT_EXCEEDED",
        "lrsAnnualLimitINR": lrs_annual_limit,
        "lrsUtilisedYTD": lrs_utilised_ytd,
        "lrsRemainingINR": lrs_remaining,
        "approvalRequired": remittance_amount_inr > 5000000,
        "remarks": "Within LRS annual limit." if eligible else "Exceeds available LRS limit for this financial year.",
        "policyVersion": "FEMA-LRS-2026",
    }


@tool
def get_purpose_codes(transaction_category: str) -> list:
    """
    Retrieve valid RBI purpose codes for a remittance category.

    :param transaction_category: Category such as LOAN_REPAYMENT, FAMILY_MAINTENANCE, INVESTMENT, EDUCATION.
    :return: A list of valid purpose code objects with code and description.
    """
    # Stub
    purpose_map = {
        "FAMILY_MAINTENANCE": [{"code": "P0001", "description": "Family maintenance and savings"}],
        "LOAN_REPAYMENT": [{"code": "P0012", "description": "Repayment of loans taken by NRI from residents"}],
        "INVESTMENT": [{"code": "P0004", "description": "Purchase of shares / securities"}, {"code": "P0005", "description": "Purchase of real estate"}],
        "EDUCATION": [{"code": "P1301", "description": "Education / student fees"}],
    }
    return purpose_map.get(transaction_category, [{"code": "UNKNOWN", "description": "Contact branch for applicable purpose code."}])
