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

# Comprehensively sanctioned country codes (OFAC primary sanctions programs).
# Any transaction to these destinations must return POTENTIAL_MATCH.
_SANCTIONED_COUNTRIES = {
    "IRN",  # Iran
    "PRK",  # North Korea (DPRK)
    "SYR",  # Syria
    "CUB",  # Cuba
    "SDN",  # Sudan
    "RUS",  # Russia (broad sector sanctions, OFAC)
    "BLR",  # Belarus
    "MMR",  # Myanmar
}

# Names that appear on OFAC/UN consolidated lists (demo fixture — add real lookup in prod)
_SANCTIONED_NAMES = {
    "john doe sanctioned",
    "al-qaeda member",
    "terrorist entity",
}


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
    # Check sanctioned destination country
    if beneficiary_country.upper() in _SANCTIONED_COUNTRIES:
        return {
            "customerId": customer_id,
            "beneficiaryName": beneficiary_name,
            "beneficiaryCountry": beneficiary_country,
            "sanctionStatus": "POTENTIAL_MATCH",
            "listsChecked": ["OFAC_SDN", "UN_CONSOLIDATED", "EU_CONSOLIDATED", "MHA_INDIA"],
            "matchDetails": [
                {
                    "list": "OFAC_SDN",
                    "matchType": "COUNTRY_SANCTIONS",
                    "matchReason": f"Destination country {beneficiary_country} is subject to comprehensive OFAC sanctions program.",
                    "confidence": 1.0,
                }
            ],
            "caseReference": "SANC-2026-BLOCKED-001",
            "screenedAt": "2026-07-15T09:01:00Z",
            "action": "STOP. Escalate to compliance-investigation-team. Do NOT execute payment.",
        }

    # Check sanctioned name (case-insensitive, partial match)
    name_lower = beneficiary_name.lower()
    for sanctioned in _SANCTIONED_NAMES:
        if sanctioned in name_lower:
            return {
                "customerId": customer_id,
                "beneficiaryName": beneficiary_name,
                "beneficiaryCountry": beneficiary_country,
                "sanctionStatus": "POTENTIAL_MATCH",
                "listsChecked": ["OFAC_SDN", "UN_CONSOLIDATED", "EU_CONSOLIDATED", "MHA_INDIA"],
                "matchDetails": [
                    {
                        "list": "UN_CONSOLIDATED",
                        "matchType": "NAME_MATCH",
                        "matchReason": f"Beneficiary name '{beneficiary_name}' matches a consolidated list entry.",
                        "confidence": 0.85,
                    }
                ],
                "caseReference": "SANC-2026-NAMEMATCH-001",
                "screenedAt": "2026-07-15T09:01:00Z",
                "action": "STOP. Escalate to compliance-investigation-team for manual review.",
            }

    # Clean — no matches
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
    # LRS annual limit: USD 250,000 ≈ ₹2,50,00,000 (25 million INR)
    LRS_ANNUAL_LIMIT = 25_000_000

    # Derive YTD utilisation from the request amount for deterministic negative-case testing:
    # - Requests ≥ ₹2 crore (20M) are treated as high-value; stub simulates ₹2Cr already utilised
    #   so that any request that together would exceed the limit returns LIMIT_EXCEEDED.
    # - Requests < ₹20L (2M) use conservative 5M utilised (standard happy path).
    if remittance_amount_inr >= 20_000_000:
        lrs_utilised_ytd = 20_000_000  # ₹2 crore already used this year
    else:
        lrs_utilised_ytd = 5_000_000   # ₹50 lakh used (happy path)

    lrs_remaining = LRS_ANNUAL_LIMIT - lrs_utilised_ytd
    eligible = remittance_amount_inr <= lrs_remaining

    return {
        "customerId": customer_id,
        "remittanceAmountINR": remittance_amount_inr,
        "destinationCountry": destination_country,
        "purposeCode": purpose_code,
        "accountType": account_type,
        "femaStatus": "ELIGIBLE" if eligible else "LIMIT_EXCEEDED",
        "lrsAnnualLimitINR": LRS_ANNUAL_LIMIT,
        "lrsUtilisedYTD": lrs_utilised_ytd,
        "lrsRemainingINR": lrs_remaining,
        "approvalRequired": remittance_amount_inr > 5_000_000,
        "remarks": (
            "Within LRS annual limit." if eligible
            else f"Exceeds available LRS limit. Remaining: ₹{lrs_remaining:,.0f}. Requested: ₹{remittance_amount_inr:,.0f}."
        ),
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
