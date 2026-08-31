#!/usr/bin/env python3
"""
scripts/fetch_config.py — Bootstrap config/env.yaml from a live WXO instance.

Given your WXO URL and credentials, this script:
  1. Authenticates (CPD token via username/password, or existing cached token)
  2. Lists all agents and resolves the 12 NRI banking agent IDs
  3. Writes (or updates) config/env.yaml with the discovered values

Usage — on-prem CPD (username/password):
    python3 scripts/fetch_config.py \
        --url https://cpd-cpd-instance.apps.YOUR_DOMAIN/orchestrate/INSTANCE \
        --username cpadmin --password YOUR_PASSWORD \
        --env-name tadn-onprem --insecure

Usage — IBM Cloud SaaS (API key):
    python3 scripts/fetch_config.py \
        --url https://REGION.assistant.watson.cloud.ibm.com/instances/INSTANCE_ID \
        --api-key YOUR_IBM_CLOUD_API_KEY

Usage — if already logged in (token cached by login.sh):
    python3 scripts/fetch_config.py \
        --url https://cpd-cpd-instance.apps.YOUR_DOMAIN/orchestrate/INSTANCE \
        --env-name tadn-onprem --insecure
"""
import argparse, json, os, sys, time, urllib3
urllib3.disable_warnings()

try:
    import requests, yaml
except ImportError:
    sys.exit("Install dependencies: pip install requests pyyaml")

_HERE      = os.path.dirname(os.path.abspath(__file__))
_ROOT      = os.path.join(_HERE, "..")
_CFG_FILE  = os.path.join(_ROOT, "config", "env.yaml")
_CREDS_FILE = os.path.expanduser("~/.cache/orchestrate/credentials.yaml")

KNOWN_AGENTS = [
    "case_supervisor_agent",
    "customer_360_agent",
    "kyc_nri_agent",
    "credit_bureau_agent",
    "credit_assessment_agent",
    "document_agent",
    "compliance_supervisor_agent",
    "aml_agent",
    "sanctions_agent",
    "fema_remittance_agent",
    "fx_agent",
    "payment_agent",
]


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _get_cpd_token(cpd_base: str, username: str, password: str, verify: bool) -> str:
    """Authenticate to CPD and return a bearer token."""
    url = cpd_base.rstrip("/") + "/icp4d-api/v1/authorize"
    r = requests.post(url, json={"username": username, "password": password},
                      verify=verify, timeout=15)
    if r.status_code not in (200, 201):
        sys.exit(f"❌  CPD auth failed: HTTP {r.status_code}\n{r.text[:400]}")
    token = r.json().get("token", "")
    if not token:
        sys.exit(f"❌  CPD auth returned no token: {r.text[:200]}")
    return token


def _load_cached_token(env_name: str) -> str:
    if not os.path.exists(_CREDS_FILE):
        return ""
    with open(_CREDS_FILE) as f:
        d = yaml.safe_load(f) or {}
    entry = d.get("auth", {}).get(env_name, {}) or {}
    token   = entry.get("wxo_mcsp_token", "")
    expiry  = entry.get("wxo_mcsp_token_expiry", 0)
    if token and expiry > int(time.time()) + 60:
        return token
    return ""


def _save_token(env_name: str, token: str) -> None:
    data = {}
    if os.path.exists(_CREDS_FILE):
        with open(_CREDS_FILE) as f:
            data = yaml.safe_load(f) or {}
    data.setdefault("auth", {})[env_name] = {
        "wxo_mcsp_token": token,
        "wxo_mcsp_token_expiry": int(time.time()) + 43200,  # 12 h
    }
    os.makedirs(os.path.dirname(_CREDS_FILE), exist_ok=True)
    with open(_CREDS_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


# ── Agent discovery ───────────────────────────────────────────────────────────

def _discover_agents(base: str, headers: dict, verify: bool) -> dict:
    """Fetch agent list and return name → full-UUID mapping.

    The /agents list endpoint caps at 10 results on some deployments and hidden
    collaborator agents may not appear in the list. This function also walks the
    collaborator chains of all visible agents to discover their hidden children.
    """
    r = requests.get(f"{base}/agents", headers=headers, verify=verify, timeout=15)
    if r.status_code != 200:
        sys.exit(f"❌  GET /agents failed: HTTP {r.status_code}\n{r.text[:300]}")
    agents_list = r.json()
    if not isinstance(agents_list, list):
        sys.exit(f"❌  Unexpected /agents response: {str(agents_list)[:200]}")

    mapping: dict = {}
    for a in agents_list:
        name = a.get("name", "")
        aid  = a.get("id", "")
        if name and aid:
            mapping[name] = aid

    # Walk collaborator chains to discover hidden agents not in the public list
    visited_ids: set = set(mapping.values())
    queue = list(mapping.values())

    while queue:
        aid = queue.pop(0)
        try:
            r2 = requests.get(f"{base}/agents/{aid}", headers=headers,
                              verify=verify, timeout=10)
            if r2.status_code != 200:
                continue
            a2 = r2.json()
            name2 = a2.get("name", "")
            if name2 and name2 not in mapping:
                mapping[name2] = aid
            for collab_id in (a2.get("collaborators") or []):
                if isinstance(collab_id, str) and collab_id not in visited_ids:
                    visited_ids.add(collab_id)
                    queue.append(collab_id)
        except Exception:
            continue

    return mapping


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Bootstrap config/env.yaml from a live WXO instance.")
    p.add_argument("--url",       required=True,
                   help="WXO instance base URL (without /v1/orchestrate)")
    p.add_argument("--username",  default="",  help="CPD username (on-prem only)")
    p.add_argument("--password",  default="",  help="CPD password (on-prem only)")
    p.add_argument("--api-key",   default="",  help="API key (IBM Cloud SaaS or on-prem)")
    p.add_argument("--env-name",  default="my-banking-env",
                   help="ADK environment name (default: my-banking-env)")
    p.add_argument("--insecure",  action="store_true",
                   help="Disable TLS verification (self-signed certs on-prem)")
    p.add_argument("--auth-type", default="",  help="cpd | ibm_iam | mcsp (auto-detected if omitted)")
    p.add_argument("--dry-run",   action="store_true",
                   help="Print the config that would be written without writing it")
    args = p.parse_args()

    WXO_URL = args.url.rstrip("/")
    VERIFY  = not args.insecure
    BASE    = WXO_URL + "/v1/orchestrate"

    # ── Resolve token ──────────────────────────────────────────────────────────
    token = ""

    # 1. Try cached token
    token = _load_cached_token(args.env_name)
    if token:
        print(f"✔  Using cached token for env '{args.env_name}'")

    # 2. CPD username/password
    if not token and args.username:
        password = args.password
        if not password:
            import getpass
            password = getpass.getpass(f"CPD password for {args.username}: ")
        # CPD base URL is everything before /orchestrate/... path
        cpd_base = WXO_URL.split("/orchestrate")[0]
        print(f"⏳  Authenticating to CPD at {cpd_base} ...")
        token = _get_cpd_token(cpd_base, args.username, password, VERIFY)
        _save_token(args.env_name, token)
        print(f"✔  CPD token obtained and cached")

    # 3. API key used directly as bearer
    if not token and args.api_key:
        token = args.api_key
        print(f"✔  Using API key as bearer token")

    if not token:
        sys.exit(
            "❌  No credentials. Provide one of:\n"
            "    --username/--password  (CPD on-prem)\n"
            "    --api-key              (IBM Cloud SaaS or CPD API key)\n"
            "    Or run: ./scripts/login.sh --gen-token first"
        )

    H = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # ── Discover agents ────────────────────────────────────────────────────────
    print(f"⏳  Fetching agents from {BASE}/agents ...")
    all_agents = _discover_agents(BASE, H, VERIFY)
    print(f"✔  Found {len(all_agents)} agents on instance")

    agent_ids = {}
    missing   = []
    for name in KNOWN_AGENTS:
        aid = all_agents.get(name, "")
        if aid:
            agent_ids[name] = aid
            print(f"  ✔  {name:<35} {aid}")
        else:
            agent_ids[name] = ""
            missing.append(name)
            print(f"  ⚠  {name:<35} NOT FOUND (deploy first)")

    if missing:
        print(f"\n⚠  {len(missing)} agents not deployed. Run: ./scripts/deploy.sh")

    # ── Build config dict ──────────────────────────────────────────────────────
    auth_type = args.auth_type
    if not auth_type:
        if "/orchestrate" in WXO_URL:
            auth_type = "cpd"
        elif "ibm.com" in WXO_URL or "watson.cloud" in WXO_URL:
            auth_type = "ibm_iam"

    config = {
        "wxo": {
            "url": WXO_URL,
            "api_key": args.api_key or "",
            "env_name": args.env_name,
            "auth_type": auth_type,
            "insecure": args.insecure,
        },
        "agents": agent_ids,
        "test": {
            "customer_id":             "CUST-NRI-88221",
            "case_id":                 "CASE-2026-00441",
            "loan_amount_inr":         7500000,
            "remittance_amount_inr":   2000000,
            "destination_country":     "SGP",
            "destination_currency":    "SGD",
        },
    }

    # ── Write (or dry-run) ─────────────────────────────────────────────────────
    if args.dry_run:
        print("\n--- config/env.yaml (dry run) ---")
        print(yaml.dump(config, default_flow_style=False, allow_unicode=True))
        print("--- (not written) ---")
        return

    os.makedirs(os.path.dirname(_CFG_FILE), exist_ok=True)
    with open(_CFG_FILE, "w") as f:
        f.write("# config/env.yaml — generated by scripts/fetch_config.py\n")
        f.write("# DO NOT COMMIT — this file is git-ignored\n\n")
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    print(f"\n✅  Written: {_CFG_FILE}")
    print("   Next: python3 scripts/test_run.py")


if __name__ == "__main__":
    main()
