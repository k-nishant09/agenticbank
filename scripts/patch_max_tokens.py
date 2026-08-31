#!/usr/bin/env python3
"""
scripts/patch_max_tokens.py — Set max_completion_tokens on all 12 NRI banking agents.

The Qwen model-gateway uses an OpenAI-compatible API. When max_completion_tokens is
null (not set), the gateway interprets it as 0, producing:

  Error: "requested 0 output tokens and your prompt contains at least 32769 input tokens"

This script PATCHes all 12 agents to set max_completion_tokens=2048 and then releases
each one to the live environment.

Usage:
    python3 scripts/patch_max_tokens.py
    python3 scripts/patch_max_tokens.py --max-tokens 4096  # override default
    python3 scripts/patch_max_tokens.py --dry-run          # print payloads only
"""
import argparse, json, os, sys, time, urllib3
urllib3.disable_warnings()

try:
    import requests, yaml
except ImportError:
    sys.exit("pip install requests pyyaml")

_HERE     = os.path.dirname(os.path.abspath(__file__))
_CFG_FILE = os.path.join(_HERE, "..", "config", "env.yaml")
_CREDS    = os.path.expanduser("~/.cache/orchestrate/credentials.yaml")

AGENT_NAMES = [
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


def _load_config():
    if not os.path.exists(_CFG_FILE):
        return {}
    with open(_CFG_FILE) as f:
        return yaml.safe_load(f) or {}


def _load_token(env_name: str) -> str:
    if not os.path.exists(_CREDS):
        return ""
    with open(_CREDS) as f:
        d = yaml.safe_load(f) or {}
    entry  = d.get("auth", {}).get(env_name, {}) or {}
    token  = entry.get("wxo_mcsp_token", "")
    expiry = entry.get("wxo_mcsp_token_expiry", 0)
    if token and expiry > int(time.time()) + 60:
        return token
    return ""


def _discover_agents(base: str, headers: dict, verify: bool) -> dict:
    """Return name → full UUID dict for all agents on the instance."""
    # Page through if needed — try ?limit=100
    r = requests.get(f"{base}/agents?limit=100&include_hidden=true", headers=headers, verify=verify, timeout=15)
    if r.status_code != 200:
        sys.exit(f"❌  GET /agents failed: {r.status_code}\n{r.text[:300]}")
    agents = r.json()
    if not isinstance(agents, list):
        sys.exit(f"❌  Unexpected /agents response shape")
    return {a["name"]: a["id"] for a in agents if a.get("name") and a.get("id")}


def _get_live_env_id(base: str, agent_id: str, headers: dict, verify: bool) -> str:
    """Return the live environment ID for an agent."""
    r = requests.get(f"{base}/agents/{agent_id}", headers=headers, verify=verify, timeout=15)
    if r.status_code != 200:
        return ""
    for env in r.json().get("environments", []):
        if env.get("name") == "live":
            return env.get("id", "")
    return ""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--max-tokens", type=int, default=2048,
                   help="max_completion_tokens to set (default: 2048)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print what would be patched, don't actually call the API")
    args = p.parse_args()

    cfg      = _load_config()
    wxo      = cfg.get("wxo", {})
    WXO_URL  = wxo.get("url", "").rstrip("/")
    ENV_NAME = wxo.get("env_name", "my-banking-env")
    INSECURE = wxo.get("insecure", False)
    VERIFY   = not INSECURE

    if not WXO_URL:
        sys.exit("❌  WXO_URL not set. Edit config/env.yaml first.")

    BASE  = WXO_URL + "/v1/orchestrate"
    TOKEN = _load_token(ENV_NAME) or wxo.get("api_key", "")

    if not TOKEN:
        sys.exit("❌  No token. Run: ./scripts/login.sh --gen-token")

    H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

    print(f"⏳  Discovering agents on {BASE} ...")
    all_agents = _discover_agents(BASE, H, VERIFY)

    results = {"patched": [], "released": [], "not_found": [], "errors": []}

    for name in AGENT_NAMES:
        aid = all_agents.get(name)
        if not aid:
            print(f"  ⚠  {name:<35} NOT FOUND — skipping")
            results["not_found"].append(name)
            continue

        llm_config_patch = {
            "llm_config": {
                "max_completion_tokens": args.max_tokens,
                # Preserve other fields at null — they inherit from the model
                "model": "",
                "decoding_method": None,
                "prompt": None,
                "max_tokens": None,
                "temperature": None,
                "top_p": None,
                "top_k": None,
            }
        }

        if args.dry_run:
            print(f"  [DRY RUN] PATCH {aid[:8]} ({name})  max_completion_tokens={args.max_tokens}")
            continue

        # PATCH the agent
        r = requests.patch(
            f"{BASE}/agents/{aid}",
            headers=H, json=llm_config_patch, verify=VERIFY, timeout=15
        )
        if r.status_code in (200, 201, 204):
            print(f"  ✔  PATCH {name:<35} {r.status_code}")
            results["patched"].append(name)
        else:
            print(f"  ✘  PATCH {name:<35} {r.status_code}: {r.text[:150]}")
            results["errors"].append(f"{name}: PATCH {r.status_code}")
            continue

        time.sleep(0.5)  # avoid hammering the API

        # Release to live environment
        live_env_id = _get_live_env_id(BASE, aid, H, VERIFY)
        if live_env_id:
            r2 = requests.post(
                f"{BASE}/agents/{aid}/releases",
                headers=H,
                json={"environment_id": live_env_id},
                verify=VERIFY, timeout=30
            )
            if r2.status_code in (200, 201):
                print(f"  ✔  RELEASE {name:<33} → live env {live_env_id[:8]}")
                results["released"].append(name)
            else:
                print(f"  ⚠  RELEASE {name:<33} {r2.status_code}: {r2.text[:150]}")
                results["errors"].append(f"{name}: RELEASE {r2.status_code}")
        else:
            print(f"  ⚠  Could not find live env ID for {name}")

        time.sleep(1)  # space out releases

    # Summary
    print(f"\n{'='*60}")
    print(f"  max_completion_tokens set to: {args.max_tokens}")
    print(f"  Patched  : {len(results['patched'])}/{len(AGENT_NAMES)}")
    print(f"  Released : {len(results['released'])}/{len(results['patched'])}")
    if results["not_found"]:
        print(f"  Not found: {results['not_found']}")
    if results["errors"]:
        print(f"  Errors   : {results['errors']}")
    if not results["errors"] and not results["not_found"]:
        print("\n  ✅  All agents patched. Run: python3 scripts/smoke_test.py")


if __name__ == "__main__":
    main()
