"""
FX and Payment tools.
IMPORTANT architectural rules:
  - FX: A QUOTE is not an EXECUTION. Customer must explicitly confirm before execution.
  - Payment: Tiered permission model. SUBMIT and EXECUTE require explicit authorization.
  - Idempotency: Every payment tool requires an idempotency_key to prevent duplicate submissions.
"""

from ibm_watsonx_orchestrate.agent_builder.tools import tool


# ─── FX ───────────────────────────────────────────────────────────────────────

@tool
def get_fx_rate(from_currency: str, to_currency: str, amount: float) -> dict:
    """
    Retrieve the current indicative FX rate and calculate the converted amount.
    This is a QUOTE only — not an execution. Customer confirmation is required before proceeding.

    :param from_currency: ISO 4217 source currency code, e.g. INR.
    :param to_currency: ISO 4217 target currency code, e.g. SGD.
    :param amount: Amount in the source currency to convert.
    :return: A dict with indicativeRate, convertedAmount, fees and quoteExpiry.
    """
    # Stub — replace with FX system / treasury rate API
    rate = 0.016  # approximate INR→SGD rate
    fees_inr = amount * 0.0025  # 0.25% conversion fee
    converted = (amount - fees_inr) * rate

    return {
        "fromCurrency": from_currency,
        "toCurrency": to_currency,
        "sourceAmount": amount,
        "indicativeRate": rate,
        "convertedAmount": round(converted, 2),
        "feeINR": round(fees_inr, 2),
        "gstOnFee": round(fees_inr * 0.18, 2),
        "totalDebitINR": round(amount, 2),
        "quoteId": "FXQ-2026-88771",
        "quoteExpiry": "2026-07-15T09:15:00Z",
        "rateType": "INDICATIVE",
        "note": "This is an indicative quote. Customer must confirm before execution.",
    }


@tool
def create_fx_quote(
    customer_id: str,
    from_currency: str,
    to_currency: str,
    amount: float,
    purpose_code: str,
) -> dict:
    """
    Create a locked FX quote for customer confirmation. Quote is valid for 15 minutes.
    DO NOT execute without customer explicit confirmation.

    :param customer_id: The bank's internal customer identifier.
    :param from_currency: ISO 4217 source currency code.
    :param to_currency: ISO 4217 target currency code.
    :param amount: Amount in source currency.
    :param purpose_code: RBI purpose code for the remittance.
    :return: A dict with quoteId, lockedRate, convertedAmount and expiryTime.
    """
    # Stub
    return {
        "customerId": customer_id,
        "quoteId": "FXLQ-2026-99221",
        "fromCurrency": from_currency,
        "toCurrency": to_currency,
        "sourceAmount": amount,
        "lockedRate": 0.01598,
        "convertedAmount": round(amount * 0.01598, 2),
        "totalFeeINR": round(amount * 0.0025, 2),
        "purposeCode": purpose_code,
        "status": "PENDING_CUSTOMER_CONFIRMATION",
        "expiryTime": "2026-07-15T09:30:00Z",
        "note": "Awaiting customer confirmation. Quote expires in 15 minutes.",
    }


# ─── PAYMENT ──────────────────────────────────────────────────────────────────

@tool
def validate_beneficiary(
    customer_id: str,
    beneficiary_account: str,
    beneficiary_bank_code: str,
    beneficiary_country: str,
    beneficiary_name: str,
) -> dict:
    """
    Validate the beneficiary account details before payment instruction creation.

    :param customer_id: The bank's internal customer identifier.
    :param beneficiary_account: Beneficiary account number or IBAN.
    :param beneficiary_bank_code: SWIFT/BIC code of the beneficiary bank.
    :param beneficiary_country: ISO 3166-1 alpha-3 country code of the beneficiary.
    :param beneficiary_name: Full legal name of the beneficiary.
    :return: A dict with isValid, validationStatus and any remarks.
    """
    # Stub — replace with beneficiary validation / SWIFT GPI lookup
    return {
        "customerId": customer_id,
        "beneficiaryAccount": beneficiary_account,
        "beneficiaryBankCode": beneficiary_bank_code,
        "beneficiaryCountry": beneficiary_country,
        "isValid": True,
        "validationStatus": "VERIFIED",
        "remarks": "Beneficiary account verified via SWIFT GPI.",
    }


@tool
def create_payment_instruction(
    customer_id: str,
    idempotency_key: str,
    source_account: str,
    beneficiary_account: str,
    beneficiary_bank_code: str,
    beneficiary_country: str,
    amount: float,
    currency: str,
    fx_quote_id: str,
    purpose_code: str,
    case_id: str,
) -> dict:
    """
    Create a payment instruction (PREPARE state). Does NOT execute the payment.
    Requires a confirmed FX quote, validated beneficiary, passed AML and sanctions.
    The idempotency_key prevents duplicate payment creation on retries.

    :param customer_id: The bank's internal customer identifier.
    :param idempotency_key: Unique key to prevent duplicate payment instructions (use case_id + attempt).
    :param source_account: Debit account number.
    :param beneficiary_account: Beneficiary account number.
    :param beneficiary_bank_code: SWIFT/BIC code.
    :param beneficiary_country: ISO 3166-1 alpha-3 country code.
    :param amount: Payment amount in source currency.
    :param currency: ISO 4217 currency code.
    :param fx_quote_id: Confirmed FX quote ID.
    :param purpose_code: RBI purpose code.
    :param case_id: Case ID from the Case Supervisor for audit traceability.
    :return: A dict with paymentInstructionId, status (PREPARED) and nextStep.
    """
    # Stub — replace with payment system API
    return {
        "customerId": customer_id,
        "idempotencyKey": idempotency_key,
        "paymentInstructionId": f"PI-{case_id}-001",
        "sourceAccount": source_account,
        "beneficiaryAccount": beneficiary_account,
        "amount": amount,
        "currency": currency,
        "fxQuoteId": fx_quote_id,
        "purposeCode": purpose_code,
        "caseId": case_id,
        "status": "PREPARED",
        "nextStep": "AWAITING_CUSTOMER_AUTHORIZATION",
        "createdAt": "2026-07-15T09:20:00Z",
    }


@tool
def get_payment_status(payment_instruction_id: str) -> dict:
    """
    Check the current status of a payment instruction before retrying.
    ALWAYS check status before retrying a payment to prevent duplicate execution.

    :param payment_instruction_id: The payment instruction ID to check.
    :return: A dict with paymentInstructionId, status and any executionDetails.
    """
    # Stub
    return {
        "paymentInstructionId": payment_instruction_id,
        "status": "PREPARED",
        "executionDetails": None,
        "swiftGpiUetr": None,
        "errorCode": None,
        "updatedAt": "2026-07-15T09:20:00Z",
    }


@tool
def submit_payment(
    payment_instruction_id: str,
    customer_authorization_token: str,
    idempotency_key: str,
) -> dict:
    """
    Submit an authorized payment instruction for execution.
    Requires a valid customer_authorization_token (OTP / digital signature).
    ALWAYS verify payment status via get_payment_status before calling this on a retry.

    :param payment_instruction_id: The prepared payment instruction ID.
    :param customer_authorization_token: OTP or digital authorization token from the customer.
    :param idempotency_key: Same idempotency_key used in create_payment_instruction.
    :return: A dict with status, swiftGpiUetr, estimatedDelivery and auditReference.
    """
    # Stub — replace with payment execution system API
    return {
        "paymentInstructionId": payment_instruction_id,
        "idempotencyKey": idempotency_key,
        "status": "SUBMITTED",
        "swiftGpiUetr": "550e8400-e29b-41d4-a716-446655440000",
        "estimatedDelivery": "2026-07-16T12:00:00Z",
        "auditReference": f"AUD-{payment_instruction_id}",
        "submittedAt": "2026-07-15T09:35:00Z",
    }
