#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# scripts/teardown.sh — Remove all Banking Platform agents and tools.
#
# WARNING: This is destructive. The agents and tools will be deleted from your
#          watsonx Orchestrate instance. Confirm before running.
#
# Usage:
#   ./scripts/teardown.sh           # interactive confirmation
#   CONFIRM=yes ./scripts/teardown.sh  # skip confirmation (CI/CD)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

if command -v orchestrate &>/dev/null; then
  ORC="orchestrate"
else
  ORC="uvx --from ibm-watsonx-orchestrate orchestrate"
fi

# ── Confirmation ──────────────────────────────────────────────────────────────
if [[ "${CONFIRM:-}" != "yes" ]]; then
  echo "⚠️  This will remove all 12 Banking Platform agents and 31 tools."
  read -rp "Type 'yes' to continue: " CONFIRM
  [[ "${CONFIRM}" != "yes" ]] && { echo "Aborted."; exit 0; }
fi

# ── Remove agents (primary first, then supervisors, then leaf) ────────────────
echo ""
echo "==> Removing agents..."
AGENTS=(
  case_supervisor_agent
  compliance_supervisor_agent
  payment_agent
  fx_agent
  credit_assessment_agent
  credit_bureau_agent
  document_agent
  kyc_nri_agent
  customer_360_agent
  fema_remittance_agent
  sanctions_agent
  aml_agent
)
for name in "${AGENTS[@]}"; do
  echo "  • ${name}"
  $ORC agents remove --name "${name}" --kind native 2>/dev/null || \
    echo "    (not found — skipping)"
done

# ── Remove tools ──────────────────────────────────────────────────────────────
echo ""
echo "==> Removing tools..."
TOOLS=(
  create_case advance_case_state get_case add_case_artifact escalate_to_human
  get_customer_profile get_account_summary get_existing_loans
  get_kyc_status verify_pan get_customer_identity get_nri_status
  get_credit_score get_credit_history
  assess_loan_eligibility get_credit_policy
  classify_document extract_document_fields validate_document check_document_completeness
  run_aml_check get_customer_risk_score screen_sanctions check_fema_eligibility get_purpose_codes
  get_fx_rate create_fx_quote
  validate_beneficiary create_payment_instruction get_payment_status submit_payment
)
for name in "${TOOLS[@]}"; do
  $ORC tools remove --name "${name}" 2>/dev/null || true
done

echo ""
echo "✅  Teardown complete."
