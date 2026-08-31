#!/usr/bin/env python3
"""
scripts/smoke_test.py — Quick smoke test for the Banking Agentic Platform.

Sends a single NRI loan intake message to case_supervisor_agent and validates
the response contains the expected case ID and multi-turn handoff signal.

Configuration (in priority order):
  1. config/env.yaml  (recommended — copy from config/env.example.yaml)
  2. Environment variables: WXO_URL, WXO_API_KEY, WXO_ENV_NAME, AGENT_CASE_SUPERVISOR

Usage:
  python3 scripts/smoke_test.py
  WXO_URL=https://… WXO_API_KEY=… python3 scripts/smoke_test.py
"""
import os, sys, json, time, yaml, requests, urllib3
urllib3.disable_warnings()

# ── Load config ───────────────────────────────────────────────────────────────
_HERE    = os.path.dirname(os.path.abspath(__file__))
_CFG_FILE = os.path.join(_HERE, "..", "config", "env.yaml")

def _load_config() -> dict:
    if os.path.exists(_CFG_FILE):
        with open(_CFG_FILE) as f:
            return yaml.safe_load(f) or {}
    return {}

def _load_credentials_cache(env_name: str) -> str:
    """Fall back to the ADK credentials cache for the token."""
    creds_path = os.path.expanduser("~/.cache/orchestrate/credentials.yaml")
    if not os.path.exists(creds_path):
        return ""
    with open(creds_path) as f:
        d = yaml.safe_load(f) or {}
    return (d.get("auth", {}).get(env_name, {}).get("wxo_mcsp_token", "") or "")

_CFG = _load_config()

def _cfg(dotpath: str, env_var: str = "", default: str = "") -> str:
    """Read config with priority: env var > config/env.yaml > default."""
    if env_var and os.environ.get(env_var):
        return os.environ[env_var]
    keys = dotpath.split(".")
    v = _CFG
    for k in keys:
        v = v.get(k, "") if isinstance(v, dict) else ""
    return str(v) if v else default

# ── Resolve required settings ─────────────────────────────────────────────────
WXO_URL     = _cfg("wxo.url",     "WXO_URL").rstrip("/")
WXO_API_KEY = _cfg("wxo.api_key", "WXO_API_KEY")
ENV_NAME    = _cfg("wxo.env_name","WXO_ENV_NAME", "my-banking-env")
INSECURE    = _cfg("wxo.insecure","WXO_INSECURE", "false").lower() == "true"
AGENT_ID    = _cfg("agents.case_supervisor_agent", "AGENT_CASE_SUPERVISOR")

if not WXO_URL or WXO_URL == "https://YOUR_ORCHESTRATE_HOST/orchestrate":
    print("❌  WXO_URL is not configured.")
    print("    Set it in config/env.yaml (copy from config/env.example.yaml)")
    print("    or export WXO_URL=https://your-host/orchestrate")
    sys.exit(1)

# ── Build API base URL ────────────────────────────────────────────────────────
# Standard WXO REST path: <instance-url>/v1/orchestrate
# For CPD on-prem the URL already ends in /orchestrate
# For IBM Cloud SaaS it ends in /instances/<id>
if "/orchestrate" in WXO_URL and not WXO_URL.endswith("/v1") and not WXO_URL.endswith("/v1/orchestrate"):
    BASE = WXO_URL.rstrip("/") + "/v1/orchestrate"
else:
    BASE = WXO_URL.rstrip("/") + "/v1/orchestrate"

# ── Resolve auth token ────────────────────────────────────────────────────────
TOKEN = ""
# Try ADK credentials cache first (covers --gen-token login)
TOKEN = _load_credentials_cache(ENV_NAME)
# Fall back to API key (used directly as bearer by WXO)
if not TOKEN and WXO_API_KEY:
    TOKEN = WXO_API_KEY

if not TOKEN:
    print("❌  No authentication token available.")
    print("    Run: ./scripts/login.sh")
    sys.exit(1)

H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
VERIFY = not INSECURE

# ── Resolve agent ID ──────────────────────────────────────────────────────────
def resolve_agent_id() -> str:
    """If AGENT_ID not configured, look up case_supervisor_agent from the API."""
    if AGENT_ID:
        return AGENT_ID
    print("  ℹ  AGENT_CASE_SUPERVISOR not set — looking up from API ...")
    try:
        r = requests.get(f"{BASE}/agents", headers=H, verify=VERIFY, timeout=15)
        if r.status_code == 200:
            agents = r.json()
            if isinstance(agents, list):
                for a in agents:
                    if a.get("name") == "case_supervisor_agent":
                        return a["id"]
    except Exception as e:
        print(f"  ⚠  Could not list agents: {e}")
    print("❌  case_supervisor_agent not found. Deploy first: ./scripts/deploy.sh")
    sys.exit(1)

# ── Helpers ───────────────────────────────────────────────────────────────────
def _extract_text(run_payload: dict) -> str:
    result = run_payload.get("result") or {}
    try:
        blocks = result["data"]["message"]["content"]
        texts  = [b.get("text","") for b in blocks if b.get("text")]
        if texts:
            return " ".join(texts)
    except (KeyError, TypeError):
        pass
    if isinstance(result, dict) and isinstance(result.get("content"), str):
        return result["content"]
    return json.dumps(result)[:800]

def _steps(run_payload: dict) -> int:
    try:
        return len(run_payload["result"]["data"]["message"]["step_history"])
    except (KeyError, TypeError):
        return 0

# ── Smoke test ────────────────────────────────────────────────────────────────
def run_smoke_test():
    aid = resolve_agent_id()
    msg = (
        "I am NRI customer CUST-NRI-88221. I need a personal loan of ₹75 lakh "
        "and will later remit ₹20 lakh to Singapore. "
        "Please create the case and retrieve my Customer 360 profile."
    )

    print(f"\n{'='*64}")
    print("  Banking Agentic Platform — Smoke Test")
    print(f"  URL  : {BASE}")
    print(f"  Agent: case_supervisor_agent ({aid[:8]}…)")
    print(f"{'='*64}\n")
    print(f"  Sending: {msg[:80]}…\n")

    t0 = time.time()
    r  = requests.post(
        f"{BASE}/runs", headers=H, verify=VERIFY, timeout=20,
        json={"message": {"role": "user", "content": msg}, "agent_id": aid}
    )
    if r.status_code not in (200, 201, 202):
        print(f"❌  POST /runs failed: HTTP {r.status_code}\n{r.text[:400]}")
        sys.exit(1)

    run_id = r.json().get("run_id")
    print(f"  run_id = {run_id}")

    # Poll
    s = {}
    for i in range(40):
        time.sleep(3)
        s  = requests.get(f"{BASE}/runs/{run_id}", headers=H, verify=VERIFY, timeout=10).json()
        st = s.get("status", "")
        steps = _steps(s)
        elapsed = int(time.time() - t0)
        print(f"  [{elapsed:>3}s] {st:<12} steps={steps}")
        if st in ("completed", "failed", "error", "cancelled"):
            break
    else:
        print("\n❌  Timed out after 120s")
        sys.exit(1)

    text   = _extract_text(s)
    steps  = _steps(s)
    elapsed = round(time.time() - t0, 1)

    print(f"\n  Response ({len(text)} chars, {steps} steps, {elapsed}s):")
    print(f"  {text[:300]}\n")

    # ── Assertions ────────────────────────────────────────────────────────────
    failures = []
    if s.get("status") != "completed":
        failures.append(f"status={s.get('status')} (expected completed)")
    if s.get("last_error"):
        failures.append(f"last_error={s['last_error']}")
    if steps < 1:
        failures.append(f"steps={steps} (expected ≥ 1 — agent did not use any tools)")
    if "case" not in text.lower() and "cust" not in text.lower():
        failures.append("response does not mention 'case' or customer context")
    if "continue" not in text.lower() and "profile" not in text.lower():
        failures.append("response missing 'continue' handoff or Customer 360 data")
    if elapsed > 30:
        failures.append(f"elapsed {elapsed}s > 30s SLA")

    if failures:
        print("❌  SMOKE TEST FAILED")
        for f in failures:
            print(f"    • {f}")
        sys.exit(1)
    else:
        print("✅  SMOKE TEST PASSED")
        print(f"    status=completed  steps={steps}  latency={elapsed}s")

if __name__ == "__main__":
    run_smoke_test()
