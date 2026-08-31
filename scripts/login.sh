#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# scripts/login.sh — Authenticate to your watsonx Orchestrate instance
#                    and activate the ADK environment.
#
# Reads configuration from (in priority order):
#   1. Environment variables  (WXO_URL, WXO_API_KEY, WXO_ENV_NAME, …)
#   2. config/env.yaml        (copy from config/env.example.yaml)
#   3. Interactive prompt     (fallback)
#
# Usage:
#   # API-key login (default)
#   ./scripts/login.sh
#
#   # Non-interactive (CI/CD)
#   WXO_URL=https://… WXO_API_KEY=… ./scripts/login.sh
#
#   # On-prem CPD: generate a session token from username/password
#   ./scripts/login.sh --gen-token
#   CPD_USERNAME=admin CPD_PASSWORD=… ./scripts/login.sh --gen-token
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_FILE="${PROJECT_ROOT}/config/env.yaml"

# ── Load config/env.yaml if present ──────────────────────────────────────────
_yaml_get() {
  # Simple key: value extractor (requires python3, handles nested wxo.key)
  local key="$1"
  python3 -c "
import yaml, sys, os
path = '${CONFIG_FILE}'
if not os.path.exists(path):
    sys.exit(0)
with open(path) as f:
    d = yaml.safe_load(f) or {}
keys = '${key}'.split('.')
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
WXO_AUTH_TYPE="${WXO_AUTH_TYPE:-$(_yaml_get wxo.auth_type)}"

# Defaults
WXO_ENV_NAME="${WXO_ENV_NAME:-my-banking-env}"
WXO_INSECURE="${WXO_INSECURE:-false}"

# ── Helpers ───────────────────────────────────────────────────────────────────
log()  { echo "[login] $*"; }
err()  { echo "[login] ERROR: $*" >&2; exit 1; }

ensure_orchestrate_cli() {
  if command -v orchestrate &>/dev/null; then
    ORCHESTRATE="orchestrate"
  else
    log "orchestrate CLI not found — using uvx shim"
    ORCHESTRATE="uvx --from ibm-watsonx-orchestrate orchestrate"
  fi
}

# ── Validate required config ──────────────────────────────────────────────────
validate_config() {
  if [[ -z "${WXO_URL}" ]]; then
    err "WXO_URL is not set. Set it in .env, config/env.yaml, or as an env var."
  fi

  # Normalise trailing slash
  WXO_URL="${WXO_URL%/}"
  CPD_BASE="${WXO_URL%/orchestrate}"
}

# ── Register environment in ADK config (idempotent) ──────────────────────────
ensure_env_registered() {
  ensure_orchestrate_cli
  local adk_config="$HOME/.config/orchestrate/config.yaml"

  if ! grep -q "${WXO_ENV_NAME}" "${adk_config}" 2>/dev/null; then
    log "Registering environment '${WXO_ENV_NAME}' → ${WXO_URL} ..."
    local insecure_flag=""
    [[ "${WXO_INSECURE}" == "true" ]] && insecure_flag="--insecure"

    local type_flag=""
    [[ -n "${WXO_AUTH_TYPE}" ]] && type_flag="--type ${WXO_AUTH_TYPE}"

    echo "y" | $ORCHESTRATE env add \
      -n "${WXO_ENV_NAME}" \
      -u "${WXO_URL}" \
      ${type_flag} \
      ${insecure_flag} 2>&1 || true

    # Ensure verify is not None (ADK quirk)
    if [[ "${WXO_INSECURE}" == "true" ]] && [[ -f "${adk_config}" ]]; then
      sed -i.bak "s/verify: None/verify: false/" "${adk_config}" 2>/dev/null || true
      rm -f "${adk_config}.bak"
    fi
  else
    log "Environment '${WXO_ENV_NAME}' already registered."
  fi
}

# ── Mode A: API-key login (standard) ─────────────────────────────────────────
api_key_mode() {
  if [[ -z "${WXO_API_KEY}" ]]; then
    echo
    echo "  Get your API key:"
    echo "    1. Open: ${WXO_URL}/build"
    echo "    2. Click user icon → Settings → API details"
    echo "    3. Click 'Generate API key' and copy it"
    echo
    read -rsp "Paste your WO API key: " WXO_API_KEY
    echo
  fi

  ensure_orchestrate_cli
  log "Activating environment '${WXO_ENV_NAME}' ..."
  $ORCHESTRATE env activate "${WXO_ENV_NAME}" --api-key "${WXO_API_KEY}"
}

# ── Mode B: CPD username/password → session token (on-prem admin only) ───────
gen_token_mode() {
  local CPD_USER="${CPD_USERNAME:-}"
  local CPD_PASS="${CPD_PASSWORD:-}"

  if [[ -z "${CPD_USER}" ]]; then
    read -rp  "CPD username: " CPD_USER
  fi
  if [[ -z "${CPD_PASS}" ]]; then
    read -rsp "CPD password for ${CPD_USER}: " CPD_PASS
    echo
  fi

  log "Fetching CPD session token for '${CPD_USER}' ..."
  local RESPONSE TOKEN
  RESPONSE=$(curl -sk -X POST "${CPD_BASE}/icp4d-api/v1/authorize" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${CPD_USER}\",\"password\":\"${CPD_PASS}\"}")
  TOKEN=$(echo "${RESPONSE}" | python3 -c \
    "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)

  if [[ -z "${TOKEN}" ]]; then
    err "Could not obtain CPD token. Response: ${RESPONSE}"
  fi

  local EXPIRY=$(( $(date +%s) + 43200 ))  # 12 hours
  local CREDS="${HOME}/.cache/orchestrate/credentials.yaml"
  mkdir -p "$(dirname "${CREDS}")"

  python3 - <<PYEOF
import yaml, os
creds_file = "${CREDS}"
data = {}
if os.path.exists(creds_file):
    with open(creds_file) as f:
        data = yaml.safe_load(f) or {}
data.setdefault('auth', {})
data['auth']['${WXO_ENV_NAME}'] = {
    'wxo_mcsp_token': '${TOKEN}',
    'wxo_mcsp_token_expiry': ${EXPIRY}
}
with open(creds_file, 'w') as f:
    yaml.dump(data, f, default_flow_style=False)
print("[login] CPD token saved to", creds_file)
PYEOF

  local adk_config="$HOME/.config/orchestrate/config.yaml"
  if [[ -f "${adk_config}" ]]; then
    sed -i.bak "s/active_environment: .*/active_environment: ${WXO_ENV_NAME}/" \
      "${adk_config}" 2>/dev/null || true
    rm -f "${adk_config}.bak"
  fi

  local EXPIRY_FMT
  EXPIRY_FMT=$(python3 -c \
    "from datetime import datetime; print(datetime.fromtimestamp(${EXPIRY}).strftime('%Y-%m-%d %H:%M'))" \
    2>/dev/null || echo "in 12 hours")
  log "Token expires: ${EXPIRY_FMT}"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  validate_config
  ensure_env_registered

  if [[ "${1:-}" == "--gen-token" ]]; then
    gen_token_mode
  else
    api_key_mode
  fi

  log "Done. Run: orchestrate agents list"
}

main "$@"
