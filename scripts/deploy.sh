#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# scripts/deploy.sh — Deploy all tools and agents to watsonx Orchestrate.
#
# Deployment order (critical — leaf agents must exist before supervisors):
#   1. Python tools  (all 8 files)
#   2. OpenAPI tools
#   3. Leaf agents   (AML, Sanctions, FEMA, Customer360, KYC, Document,
#                     Credit Bureau, Credit Assessment, FX, Payment)
#   4. Supervisors   (Compliance Supervisor)
#   5. Primary       (Case Supervisor — must be last)
#
# Usage:
#   ./scripts/deploy.sh               # deploy everything
#   ./scripts/deploy.sh --tools-only  # deploy tools only
#   ./scripts/deploy.sh --agents-only # deploy agents only
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── Eval gate (runs before any deployment) ────────────────────────────────────
# Runs the offline evaluation suites to verify agent policy logic and guardrails
# are correct before deploying. Compliance suites have zero-tolerance thresholds.
# Pass --skip-evals to bypass (only for emergency hotfix deployments).
run_eval_gate() {
  local SKIP_EVALS=false
  for arg in "$@"; do
    [[ "$arg" == "--skip-evals" ]] && SKIP_EVALS=true
  done

  if [[ "${SKIP_EVALS}" == "true" ]]; then
    echo ""
    echo "⚠️   --skip-evals flag set. Bypassing eval gate."
    echo "    This should only be used for emergency hotfix deployments."
    echo "    Ensure evals are run manually after deployment: python3 evals/run_evals.py"
    return 0
  fi

  echo ""
  echo "==> Running eval gate (must pass before deployment)..."

  if ! command -v python3 &>/dev/null; then
    echo "  ⚠️   python3 not found — skipping eval gate."
    return 0
  fi

  if [[ ! -f "${ROOT}/evals/run_evals.py" ]]; then
    echo "  ⚠️   evals/run_evals.py not found — skipping eval gate."
    return 0
  fi

  python3 "${ROOT}/evals/run_evals.py" --ci
  local EXIT_CODE=$?

  if [[ $EXIT_CODE -ne 0 ]]; then
    echo ""
    echo "❌  EVAL GATE FAILED — deployment blocked."
    echo "    Fix failing eval cases before deploying."
    echo "    Run:  python3 evals/run_evals.py --verbose"
    exit 1
  fi

  echo "✅  Eval gate passed."
}

# ── Resolve CLI ───────────────────────────────────────────────────────────────
if command -v orchestrate &>/dev/null; then
  ORC="orchestrate"
else
  ORC="uvx --from ibm-watsonx-orchestrate orchestrate"
fi

TOOLS_ONLY=false
AGENTS_ONLY=false
for arg in "$@"; do
  [[ "$arg" == "--tools-only"  ]] && TOOLS_ONLY=true
  [[ "$arg" == "--agents-only" ]] && AGENTS_ONLY=true
done


# ── Deploy tools ──────────────────────────────────────────────────────────────
deploy_tools() {
  echo ""
  echo "==> Deploying Python tools..."
  local PYTHON_TOOLS=(
    "tools/python/guardrail_tools.py"
    "tools/python/case_management_tools.py"
    "tools/python/customer_360_tools.py"
    "tools/python/kyc_tools.py"
    "tools/python/credit_bureau_tools.py"
    "tools/python/credit_assessment_tools.py"
    "tools/python/document_tools.py"
    "tools/python/compliance_tools.py"
    "tools/python/fx_payment_tools.py"
  )
  for f in "${PYTHON_TOOLS[@]}"; do
    if [[ -f "${ROOT}/${f}" ]]; then
      echo "  • ${f}"
      $ORC tools import -k python -f "${ROOT}/${f}"
    fi
  done

  echo ""
  echo "==> Deploying OpenAPI tools..."
  for f in "${ROOT}"/tools/openapi/*.yaml "${ROOT}"/tools/openapi/*.json; do
    # Skip example/template files
    [[ "$f" == *example* ]] && continue
    if [[ -f "$f" ]]; then
      echo "  • $(basename "$f")"
      $ORC tools import -k openapi -f "$f"
    fi
  done
}

# ── Deploy agents (ordered) ───────────────────────────────────────────────────
deploy_agents() {
  echo ""
  echo "==> Deploying agents (leaf → supervisors → primary)..."

  # Leaf compliance agents
  local AGENT_ORDER=(
    "agents/native/aml_agent.yaml"
    "agents/native/sanctions_agent.yaml"
    "agents/native/fema_remittance_agent.yaml"
    "agents/native/customer_360_agent.yaml"
    "agents/native/kyc_nri_agent.yaml"
    "agents/native/document_agent.yaml"
    "agents/native/credit_bureau_agent.yaml"
    "agents/native/credit_assessment_agent.yaml"
    "agents/native/fx_agent.yaml"
    "agents/native/payment_agent.yaml"
    "agents/native/compliance_supervisor_agent.yaml"
    "agents/native/case_supervisor_agent.yaml"
  )

  for f in "${AGENT_ORDER[@]}"; do
    if [[ -f "${ROOT}/${f}" ]]; then
      local name
      name=$(basename "$f" .yaml)
      echo "  • ${name}"
      $ORC agents import -f "${ROOT}/${f}"
    fi
  done
}

# ── List result ───────────────────────────────────────────────────────────────
print_summary() {
  echo ""
  echo "==> Deployed agents:"
  $ORC agents list 2>/dev/null || true
  echo ""
  echo "✅  Deploy complete."
  echo ""
  echo "    Record your agent IDs in config/env.yaml under the 'agents:' section,"
  echo "    then run the smoke test:"
  echo "      python3 scripts/smoke_test.py"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  run_eval_gate "$@"
  if [[ "${AGENTS_ONLY}" == "false" ]]; then
    deploy_tools
  fi
  if [[ "${TOOLS_ONLY}" == "false" ]]; then
    deploy_agents
  fi
  print_summary
}

main "$@"
