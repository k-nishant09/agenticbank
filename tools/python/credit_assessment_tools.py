"""
Credit Assessment tools — apply bank credit policy to bureau + income + exposure data.
Returns PRELIMINARY_ELIGIBLE | MANUAL_REVIEW_REQUIRED | NOT_ELIGIBLE.
The agent surfaces this output; it does NOT override policy rules.
"""

from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool
def assess_loan_eligibility(
    customer_id: str,
    loan_amount: float,
    loan_product: str,
    credit_score: int,
    monthly_income: float,
    existing_emi: float,
    existing_exposure: float,
    customer_segment: str,
) -> dict:
    """
    Evaluate preliminary loan eligibility based on bank credit policy rules (FOIR, LTV, DTI).
    This is a deterministic policy engine call — not an LLM decision.

    :param customer_id: The bank's internal customer identifier.
    :param loan_amount: Requested loan amount in INR.
    :param loan_product: Loan product code, e.g. PERSONAL_LOAN, HOME_LOAN, LAP.
    :param credit_score: CIBIL score retrieved from bureau.
    :param monthly_income: Gross monthly income in INR.
    :param existing_emi: Total existing EMI obligations in INR per month.
    :param existing_exposure: Total outstanding loan exposure in INR.
    :param customer_segment: Customer segment, e.g. MASS, AFFLUENT, HNI.
    :return: A dict with eligibilityStatus, maxEligibleAmount, foir, dti and remarks.
    """
    # Stub — replace with Loan Origination System eligibility API or decision table
    proposed_emi = loan_amount * 0.009  # approximate EMI factor
    foir = (existing_emi + proposed_emi) / monthly_income

    if credit_score < 650:
        status = "NOT_ELIGIBLE"
        remarks = "Credit score below minimum threshold of 650."
    elif foir > 0.65:
        status = "MANUAL_REVIEW_REQUIRED"
        remarks = f"FOIR {foir:.2%} exceeds 65% policy limit. Manual credit review required."
    elif credit_score >= 750 and foir <= 0.50:
        status = "PRELIMINARY_ELIGIBLE"
        remarks = "Meets all automated eligibility criteria."
    else:
        status = "MANUAL_REVIEW_REQUIRED"
        remarks = "Borderline profile; referred for manual credit assessment."

    max_eligible = monthly_income * 0.50 * 12 * 5  # simplified 5-year income multiplier

    return {
        "customerId": customer_id,
        "loanProduct": loan_product,
        "requestedAmount": loan_amount,
        "eligibilityStatus": status,
        "maxEligibleAmount": max_eligible,
        "foir": round(foir, 4),
        "creditScore": credit_score,
        "policyVersion": "CP-2026-v3",
        "remarks": remarks,
    }


@tool
def get_credit_policy(loan_product: str, customer_segment: str) -> dict:
    """
    Retrieve the applicable credit policy parameters for a loan product and segment.

    :param loan_product: Loan product code, e.g. PERSONAL_LOAN, HOME_LOAN.
    :param customer_segment: Customer segment, e.g. MASS, AFFLUENT, HNI.
    :return: A dict with minCreditScore, maxFOIR, maxDTI, maxLoanAmount and requiredDocuments.
    """
    # Stub
    return {
        "loanProduct": loan_product,
        "customerSegment": customer_segment,
        "minCreditScore": 700,
        "maxFOIR": 0.60,
        "maxDTI": 0.45,
        "maxLoanAmount": 10000000,
        "minIncome": 50000,
        "maxTenureMonths": 84,
        "requiredDocuments": ["SALARY_SLIPS_3M", "BANK_STATEMENT_6M", "ITR_2Y", "ID_PROOF", "ADDRESS_PROOF"],
        "policyVersion": "CP-2026-v3",
        "effectiveDate": "2026-01-01",
    }
