#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# scripts/setup-env.sh — One-time setup: install the ADK and register your
#                         watsonx Orchestrate environment.
#
# Prerequisites:
#   python3 >= 3.10, pip, and either uv (recommended) or pip globally available.
#
# Configuration (provide via env vars or config/env.yaml):
#   WXO_URL       — watsonx Orchestrate service URL
#   WXO_API_KEY   — API key from: WXO_URL/build → Settings → API details
#   WXO_ENV_NAME  — label for this environment (default: my-banking-env)
#
# Usage:
#   # Using env vars
#   WXO_URL=https://… WXO_API_KEY=… ./scripts/setup-env.sh
#
#   # Using config/env.yaml (recommended)
#   cp config/env.example.yaml config/env.yaml
#   # edit config/env.yaml
#   ./scripts/setup-env.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_FILE="${PROJECT_ROOT}/config/env.yaml"

# ── Load config/env.yaml ─────────────────────────────────────────────────────
_yaml_get() {
  python3 -c "
import yaml, os
path = '${CONFIG_FILE}'
if not os.path.exists(path): sys.exit(0)
import sys
with open(path) as f:
    d = yaml.safe_load(f) or {}
keys = '${1}'.split('.')
v = d
for k in keys:
    v = v.get(k, '') if isinstance(v, dict) else ''
print(v or '', end='')
" 2>/dev/null || true
}

WXO_URL="${WXO_URL:-$(_yaml_get wxo.url)}"
WXO_API_KEY="${WXO_API_KEY:-$(_yaml_get wxo.api_key)}"
WXO_ENV_NAME="${WXO_ENV_NAME:-$(_yaml_get wxo.env_name)}"
WXO_INSECURE="${WXO_INSECURE:-$(_yaml_get wxo.insecure)}"

WXO_ENV_NAME="${WXO_ENV_NAME:-my-banking-env}"

# ── Validate ──────────────────────────────────────────────────────────────────
if [[ -z "${WXO_URL}" ]]; then
  echo "❌  WXO_URL is not set."
  echo "    Set it in config/env.yaml or: export WXO_URL=https://…"
  exit 1
fi
if [[ -z "${WXO_API_KEY}" ]]; then
  echo "❌  WXO_API_KEY is not set."
  echo "    Set it in config/env.yaml or: export WXO_API_KEY=…"
  exit 1
fi

WXO_URL="${WXO_URL%/}"

# ── 1. Install the ADK ────────────────────────────────────────────────────────
echo "==> Installing ibm-watsonx-orchestrate ADK..."
pip install --upgrade ibm-watsonx-orchestrate
echo "    ADK version: $(orchestrate --version 2>/dev/null || uvx --from ibm-watsonx-orchestrate orchestrate --version)"

# ── 2. Register the environment ───────────────────────────────────────────────
# Auth type is auto-detected from the URL:
#   *.cloud.ibm.com / *.ibm.com  → ibm_iam
#   *.aws.* / *.watsonxorchestrate.* → mcsp
#   on-prem CPD                  → cpd
echo "==> Registering environment '${WXO_ENV_NAME}' → ${WXO_URL} ..."
INSECURE_FLAG=""
[[ "${WXO_INSECURE}" == "true" ]] && INSECURE_FLAG="--insecure"

orchestrate env add \
  -n "${WXO_ENV_NAME}" \
  -u "${WXO_URL}" \
  ${INSECURE_FLAG} 2>/dev/null || true  # idempotent — already registered is fine

# ── 3. Activate ───────────────────────────────────────────────────────────────
echo "==> Activating environment '${WXO_ENV_NAME}' ..."
orchestrate env activate "${WXO_ENV_NAME}" --api-key "${WXO_API_KEY}"

echo ""
echo "✅  Environment '${WXO_ENV_NAME}' is ready."
echo ""
echo "    Next step — deploy all agents and tools:"
echo "      ./scripts/deploy.sh"
echo ""
echo "    Note: Authentication tokens expire every 2 hours."
echo "    Re-authenticate with: ./scripts/login.sh"
