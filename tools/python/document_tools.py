"""
Document Intelligence tools — classify, extract, validate and track completeness of
customer-submitted documents (salary slips, bank statements, passport, ITR, etc.).
watsonx.ai provides extraction intelligence; Orchestrate coordinates the activity.
"""

from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool
def classify_document(document_id: str, document_bytes_base64: str) -> dict:
    """
    Classify the type of a submitted document using AI document understanding.

    :param document_id: Unique identifier assigned to the uploaded document.
    :param document_bytes_base64: Base64-encoded document content.
    :return: A dict with documentType, confidence and extractedMetadata.
    """
    # Stub — replace with watsonx.ai document classification API
    return {
        "documentId": document_id,
        "documentType": "SALARY_SLIP",
        "confidence": 0.97,
        "pageCount": 1,
        "language": "ENGLISH",
        "extractedMetadata": {
            "employer": "Tech Corp Ltd",
            "month": "June 2026",
            "grossSalary": 145000,
        },
    }


@tool
def extract_document_fields(document_id: str, document_type: str) -> dict:
    """
    Extract structured key fields from a classified document.

    :param document_id: Unique identifier of the document.
    :param document_type: Document type returned by classify_document.
    :return: A dict with the extracted key-value fields for that document type.
    """
    # Stub — replace with watsonx.ai extraction
    return {
        "documentId": document_id,
        "documentType": document_type,
        "fields": {
            "employerName": "Tech Corp Ltd",
            "employeeId": "EMP-9901",
            "grossMonthlyIncome": 145000,
            "netMonthlyIncome": 112000,
            "deductions": 33000,
            "month": "June 2026",
        },
        "extractionConfidence": 0.95,
    }


@tool
def check_document_completeness(customer_id: str, loan_product: str, submitted_document_ids: list) -> dict:
    """
    Compare submitted documents against the required document checklist for a loan product
    and return a list of missing items.

    :param customer_id: The bank's internal customer identifier.
    :param loan_product: Loan product code, e.g. PERSONAL_LOAN.
    :param submitted_document_ids: List of document IDs already submitted and classified.
    :return: A dict with isComplete, missingDocuments and completenessPercent.
    """
    # Stub
    required = ["SALARY_SLIPS_3M", "BANK_STATEMENT_6M", "ITR_2Y", "ID_PROOF", "ADDRESS_PROOF"]
    submitted_types = ["SALARY_SLIP", "BANK_STATEMENT", "ITR", "PASSPORT"]  # derived from submitted IDs in real impl
    missing = [r for r in required if not any(r.startswith(s[:5]) for s in submitted_types)]

    return {
        "customerId": customer_id,
        "loanProduct": loan_product,
        "isComplete": len(missing) == 0,
        "requiredDocuments": required,
        "missingDocuments": missing,
        "completenessPercent": round((len(required) - len(missing)) / len(required) * 100, 1),
    }


@tool
def validate_document(document_id: str, document_type: str) -> dict:
    """
    Validate authenticity and integrity checks on a submitted document.

    :param document_id: Unique identifier of the document.
    :param document_type: Document type (e.g. PASSPORT, SALARY_SLIP, ITR).
    :return: A dict with isValid, validationChecks and any failureReasons.
    """
    # Stub
    return {
        "documentId": document_id,
        "documentType": document_type,
        "isValid": True,
        "validationChecks": {
            "tamperDetection": "PASSED",
            "expiryCheck": "PASSED",
            "nameConsistency": "PASSED",
            "digitalSignature": "NOT_APPLICABLE",
        },
        "failureReasons": [],
    }
