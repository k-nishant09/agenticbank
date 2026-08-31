#!/usr/bin/env python3
"""
scripts/test_run.py — Quick single-run test for case_supervisor_agent.

Sends the NRI loan intake message and prints the full response.

Configuration (config/env.yaml or env vars — see config/env.example.yaml):
  WXO_URL, WXO_API_KEY / WXO_ENV_NAME, AGENT_CASE_SUPERVISOR

Usage:
  python3 scripts/test_run.py
"""
import os, sys, json, time, yaml, requests, urllib3
urllib3.disable_warnings()

# ── Config loader (shared pattern with smoke_test.py) ────────────────────────
_HERE     = os.path.dirname(os.path.abspath(__file__))
_CFG_FILE = os.path.join(_HERE, "..", "config", "env.yaml")

def _load_config() -> dict:
    if os.path.exists(_CFG_FILE):
        with open(_CFG_FILE) as f:
            return yaml.safe_load(f) or {}
    return {}

def _load_token(env_name: str) -> str:
    creds = os.path.expanduser("~/.cache/orchestrate/credentials.yaml")
    if not os.path.exists(creds):
        return ""
    with open(creds) as f:
        d = yaml.safe_load(f) or {}
    return d.get("auth", {}).get(env_name, {}).get("wxo_mcsp_token", "") or ""

_CFG = _load_config()

def _cfg(dotpath: str, env_var: str = "", default: str = "") -> str:
    if env_var and os.environ.get(env_var):
        return os.environ[env_var]
    keys = dotpath.split(".")
    v = _CFG
    for k in keys:
        v = v.get(k, "") if isinstance(v, dict) else ""
    return str(v) if v else default

WXO_URL  = _cfg("wxo.url",     "WXO_URL").rstrip("/")
ENV_NAME = _cfg("wxo.env_name","WXO_ENV_NAME","my-banking-env")
INSECURE = _cfg("wxo.insecure","WXO_INSECURE","false").lower() == "true"
AID      = _cfg("agents.case_supervisor_agent","AGENT_CASE_SUPERVISOR")
VERIFY   = not INSECURE

if not WXO_URL or "YOUR_ORCHESTRATE_HOST" in WXO_URL:
    sys.exit("❌  WXO_URL not set. Edit config/env.yaml or export WXO_URL=…")

BASE  = WXO_URL.rstrip("/") + "/v1/orchestrate"
TOKEN = _load_token(ENV_NAME) or _cfg("wxo.api_key","WXO_API_KEY")

if not TOKEN:
    sys.exit("❌  No token. Run: ./scripts/login.sh")

if not AID:
    # Auto-discover from API
    r = requests.get(f"{BASE}/agents",
                     headers={"Authorization": f"Bearer {TOKEN}"},
                     verify=VERIFY, timeout=15)
    if r.status_code == 200:
        agents = r.json()
        if isinstance(agents, list):
            for a in agents:
                if a.get("name") == "case_supervisor_agent":
                    AID = a["id"]; break
    if not AID:
        sys.exit("❌  case_supervisor_agent not found. Deploy first: ./scripts/deploy.sh")

H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# ── Send run ──────────────────────────────────────────────────────────────────
r = requests.post(
    f"{BASE}/runs", headers=H, verify=VERIFY, timeout=20,
    json={
        "message": {
            "role": "user",
            "content": (
                "I am NRI customer CUST-NRI-88221. I need a personal loan of ₹75 lakh "
                "and will later remit ₹20 lakh to Singapore. "
                "Please create the case and retrieve my Customer 360 profile."
            ),
        },
        "agent_id": AID,
    }
)
data   = r.json()
run_id = data.get("run_id")
print(f"run_id : {run_id}")
print(f"task_id: {data.get('task_id')}")

# ── Poll ──────────────────────────────────────────────────────────────────────
s = {}
for i in range(40):
    time.sleep(3)
    s  = requests.get(f"{BASE}/runs/{run_id}", headers=H, verify=VERIFY, timeout=10).json()
    st = s.get("status", "")
    print(f"  [{(i+1)*3:>3}s] {st:<12} last_error={s.get('last_error')}")
    if st in ("completed", "failed", "error", "success", "cancelled"):
        if st == "completed":
            c = s.get("result", {})
            # Try nested WXO envelope first
            text = ""
            try:
                text = c["data"]["message"]["content"][0]["text"]
            except (KeyError, IndexError, TypeError):
                pass
            if not text:
                text = c.get("content", "") if isinstance(c, dict) else str(c)
            if not text:
                text = json.dumps(c, indent=2)
            steps = len(
                s.get("result", {}).get("data", {})
                 .get("message", {}).get("step_history", [])
            )
            print(f"\n=== AGENT RESPONSE ({len(text)} chars, {steps} steps) ===")
            print(text[:1500])
        else:
            print(f"\n=== FINAL STATE ===\n{json.dumps(s, indent=2)[:800]}")
        break
else:
    print(f"\nTimed out after 120s. last_error={s.get('last_error')}")
    print(json.dumps(s, indent=2)[:400])
