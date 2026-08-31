# Banking Agentic Platform — Integration Guide

**How to connect the 12 deployed agents to your enterprise banking systems.**

This guide takes you from stub tools to production-ready integrations in 10 steps.
All agent definitions, tool files, and configuration live in `orchestrate-project/`.

---

## Platform topology

```
case_supervisor_agent  [UI-visible]
│
├── customer_360_agent
├── kyc_nri_agent
├── credit_bureau_agent
├── credit_assessment_agent
├── document_agent
├── compliance_supervisor_agent
│   ├── aml_agent
│   ├── sanctions_agent
│   └── fema_remittance_agent
├── fx_agent
└── payment_agent
```

> After deploying, run `python3 scripts/fetch_config.py` to auto-discover all agent IDs
> and populate `config/env.yaml` under the `agents:` section.

---

## Step 1 — Replace tool stubs with real API connections

Every tool in `tools/python/` currently returns hard-coded stub data.
For each domain, replace the stub body with a real HTTP call to your enterprise system.

### Pattern

```python
# BEFORE (stub)
@tool
def get_credit_score(customer_id: str, pan_number: str) -> dict:
    return {"creditScore": 781, ...}   # ← stub

# AFTER (real integration)
@tool
def get_credit_score(customer_id: str, pan_number: str) -> dict:
    resp = requests.get(
        f"{CIBIL_API_BASE}/scores",
        params={"customerId": customer_id, "pan": pan_number},
        headers={"Authorization": f"Bearer {get_cibil_token()}"},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()
```

### Tool-to-system mapping

| Tool file | Tools | Replace stub with call to |
|---|---|---|
| `customer_360_tools.py` | `get_customer_profile`, `get_account_summary`, `get_existing_loans` | CRM API + Core Banking System (CBS) |
| `kyc_tools.py` | `get_kyc_status`, `verify_pan`, `get_customer_identity`, `get_nri_status` | KYC system / CKYC Central Registry |
| `credit_bureau_tools.py` | `get_credit_score`, `get_credit_history` | CIBIL / TransUnion API |
| `credit_assessment_tools.py` | `assess_loan_eligibility`, `get_credit_policy` | Loan Origination System (LOS) or decision engine |
| `document_tools.py` | `classify_document`, `extract_document_fields`, `validate_document`, `check_document_completeness` | watsonx.ai Document Intelligence API |
| `compliance_tools.py` | `run_aml_check`, `get_customer_risk_score` | AML engine (Actimize / SAS AML) |
| `compliance_tools.py` | `screen_sanctions` | Sanctions screening service (Refinitiv WorldCheck / Dow Jones) |
| `compliance_tools.py` | `check_fema_eligibility`, `get_purpose_codes` | FEMA/LRS tracking system |
| `fx_payment_tools.py` | `get_fx_rate`, `create_fx_quote` | Treasury / FX system |
| `fx_payment_tools.py` | `validate_beneficiary`, `create_payment_instruction`, `submit_payment`, `get_payment_status` | Payment system / SWIFT GPI |
| `case_management_tools.py` | all | Case Management System (CMS) / workflow engine |
| `guardrail_tools.py` | `record_agent_call`, `get_case_call_counts` | Replace in-memory `_call_counts` dict with durable store (Redis / CMS) |

---

## Step 2 — Add API credentials as Orchestrate Connections

Never hardcode secrets in tool files. Use Orchestrate Connections to inject credentials
at runtime. The connection is created once; the ADK injects credentials into the tool
automatically when the agent calls it.

### Create a connection for each backend system

```bash
# Example: create a connection for the CIBIL API
uvx --from ibm-watsonx-orchestrate orchestrate connections create \
  --app-id cibil-api-connection

# Configure the connection type (API key, Bearer, OAuth, etc.)
uvx --from ibm-watsonx-orchestrate orchestrate connections configure \
  --app-id cibil-api-connection \
  --environment draft \
  --type team \
  --kind api_key

# Set the credentials
uvx --from ibm-watsonx-orchestrate orchestrate connections set-credentials \
  --app-id cibil-api-connection \
  --environment draft \
  --api-key "<your-cibil-api-key>"

# Repeat for live environment before promoting agents to production
uvx --from ibm-watsonx-orchestrate orchestrate connections configure \
  --app-id cibil-api-connection \
  --environment live \
  --type team \
  --kind api_key

uvx --from ibm-watsonx-orchestrate orchestrate connections set-credentials \
  --app-id cibil-api-connection \
  --environment live \
  --api-key "<your-live-cibil-api-key>"
```

### Connections to create (one per backend system)

| Connection ID | Backend | Auth kind |
|---|---|---|
| `crm-api-connection` | CRM / CBS | `bearer` or `oauth_auth_client_credentials_flow` |
| `kyc-api-connection` | KYC / CKYC | `api_key` |
| `cibil-api-connection` | CIBIL / TransUnion | `api_key` |
| `los-api-connection` | Loan Origination System | `bearer` |
| `docai-api-connection` | watsonx.ai Document AI | `bearer` |
| `aml-api-connection` | AML engine | `bearer` |
| `sanctions-api-connection` | Sanctions screening | `api_key` |
| `fema-api-connection` | FEMA/LRS system | `bearer` |
| `fx-api-connection` | FX / Treasury | `bearer` |
| `payment-api-connection` | Payment system | `oauth_auth_client_credentials_flow` |
| `cms-api-connection` | Case Management System | `bearer` |

### Reference credentials in tool files

```python
from ibm_watsonx_orchestrate.agent_builder.tools import tool, expect_credentials

@tool
@expect_credentials("cibil-api-connection")
def get_credit_score(customer_id: str, pan_number: str, credentials=None) -> dict:
    api_key = credentials.get("api_key")
    resp = requests.get(
        "https://api.cibil.com/v2/scores",
        params={"customerId": customer_id, "pan": pan_number},
        headers={"X-API-Key": api_key},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()
```

---

## Step 3 — Re-import updated tools

After replacing stubs with real API calls, re-import each tool file.
The updated tool replaces the stub in-place — no agent changes needed.

```bash
cd orchestrate-project

# Re-import each tool file (with connection binding)
uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/customer_360_tools.py --app-id crm-api-connection

uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/kyc_tools.py --app-id kyc-api-connection

uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/credit_bureau_tools.py --app-id cibil-api-connection

uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/credit_assessment_tools.py --app-id los-api-connection

uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/document_tools.py --app-id docai-api-connection

uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/compliance_tools.py --app-id aml-api-connection

uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/fx_payment_tools.py --app-id payment-api-connection

uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/case_management_tools.py --app-id cms-api-connection
```

> **Note:** `guardrail_tools.py` does not call external APIs — no `--app-id` needed.
> Re-import it only if you modify the guardrail logic itself.

---

## Step 4 — Connect tools to agents via app_id

The `--app-id` flag at import time binds the tool to the connection. If you need to
re-bind an existing tool to a different connection, re-import with the new `--app-id`.

```bash
# Example: re-bind credit bureau tool to a new connection
uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/credit_bureau_tools.py \
  --app-id cibil-api-connection
```

---

## Step 5 — Import the Core Banking OpenAPI tool

The OpenAPI spec at `tools/openapi/core-banking-api.yaml` defines the CBS API facade.
Replace the `servers.url` field with your actual CBS API Gateway URL, then import:

```bash
# Edit the spec first
nano tools/openapi/core-banking-api.yaml
# Change: url: https://api.bank.internal/cbs/v1
# To:     url: https://<your-actual-api-gateway>/cbs/v1

# Import with the CRM/CBS connection
uvx --from ibm-watsonx-orchestrate orchestrate tools import -k openapi \
  tools/openapi/core-banking-api.yaml \
  --app-id crm-api-connection
```

Then add the CBS tools (`getAccount`, `getCustomerAccounts`, `getCustomerLoans`) to
`customer_360_agent` via the UI or by updating the agent YAML and re-importing.

---

## Step 6 — Test the agent chain end-to-end

Open the supervisor agent in the UI Preview panel:

```
<your-wxo-url>/build
# Click case_supervisor_agent → Preview
```

### Smoke test messages (use the Preview panel)

**Test 1 — Loan eligibility**
```
I am NRI customer CUST-NRI-88221. I need a ₹75 lakh personal loan.
Please create the case.
```
Expected path: `case_supervisor` → `customer_360_agent` → `kyc_nri_agent` → `credit_bureau_agent` → `credit_assessment_agent`

**Test 2 — Full NRI journey**
```
I need a ₹75L loan and want to transfer ₹20 lakh to my Singapore account after approval.
Customer ID: CUST-NRI-88221.
```
Expected path: full 8-turn flow → human approval gate → FX quote → payment

**Test 3 — Compliance block**
```
Run compliance for CUST-NRI-88221. Transfer ₹20L to beneficiary John Doe in Iran.
Purpose: business.
```
Expected path: `compliance_supervisor_agent` → `aml_agent` (PASS) → `sanctions_agent` → POTENTIAL_MATCH → STOP → escalate to human

For the full set of test prompts, see [RUNBOOK.md §6](RUNBOOK.md#6-test-prompts-per-agent).

---

## Step 7 — Connect to your digital banking channel

### Option A — Webchat embed (quickest)

Generate the embed code for your web/mobile portal:

```bash
uvx --from ibm-watsonx-orchestrate orchestrate channels webchat generate \
  --agent-name case_supervisor_agent \
  --environment draft
```

Paste the generated `<script>` snippet into your banking portal HTML.

### Option B — REST API (mobile app / backend)

Use the Orchestrate chat API directly from your digital banking backend:

```python
import requests, time

BASE     = "<your-wxo-url>"                   # from config/env.yaml wxo.url
AGENT_ID = "<case_supervisor_agent-id>"       # from: python3 scripts/fetch_config.py
TOKEN    = "<your-api-key-or-session-token>"  # from: ./scripts/login.sh

# Start a conversation run
r = requests.post(
    f"{BASE}/v1/orchestrate/runs",
    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    json={"message": {"role": "user", "content": "I need a ₹75 lakh personal loan."},
          "agent_id": AGENT_ID},
    verify=True,   # set to False only in dev/test with self-signed TLS
)
run_id = r.json()["run_id"]

# Poll until status == "completed" (or "failed")
for _ in range(30):
    time.sleep(3)
    s = requests.get(
        f"{BASE}/v1/orchestrate/runs/{run_id}",
        headers={"Authorization": f"Bearer {TOKEN}"},
    ).json()
    if s.get("status") in ("completed", "failed", "error"):
        break

# Extract response text — handle both response shapes
result = s.get("result", {})
try:
    content = result["data"]["message"]["content"][0]["text"]
except (KeyError, IndexError, TypeError):
    content = result.get("content", "")
print(content)
```

### Option C — Twilio WhatsApp / SMS

```bash
uvx --from ibm-watsonx-orchestrate orchestrate channels create \
  --agent-name case_supervisor_agent \
  --environment draft \
  --channel-type twilio_whatsapp \
  --name "Banking WhatsApp" \
  --account-sid "<TWILIO_ACCOUNT_SID>" \
  --auth-token "<TWILIO_AUTH_TOKEN>" \
  --from-number "+1234567890"
```

### Option D — Microsoft Teams

```bash
uvx --from ibm-watsonx-orchestrate orchestrate channels create \
  --agent-name case_supervisor_agent \
  --environment draft \
  --channel-type teams \
  --name "Banking Teams Bot"
```

---

## Step 8 — Set up human-in-the-loop

The agents call `escalate_to_human()` at three mandatory gates:

1. **Credit review** — borderline FOIR → `MANUAL_REVIEW_REQUIRED`, queue: `credit-committee`
2. **Compliance review** — AML / Sanctions flag, queue: `compliance-investigation-team`
3. **Payment authorization** — high-value payment gate, queue: `credit-approvals-team`

### Wire escalation to your task queue

Replace the stub in `case_management_tools.py` → `escalate_to_human()` with a call to
your human task system:

```python
@tool
def escalate_to_human(
    case_id: str,
    reason: str,
    escalation_type: str,
    assigned_queue: str,
) -> dict:
    # ── Option A: Orchestrate built-in human task ─────────────────────────────
    from ibm_watsonx_orchestrate.agent_builder.tools import create_human_task
    task = create_human_task(
        title=f"Case {case_id} — {escalation_type}",
        description=reason,
        assignee_queue=assigned_queue,
    )
    return {"escalationId": task.id, "state": "HUMAN_REVIEW", "slaHours": 4}

    # ── Option B: ServiceNow ──────────────────────────────────────────────────
    resp = requests.post(
        "https://<your-snow>.service-now.com/api/now/table/incident",
        auth=("<user>", "<pass>"),
        json={
            "short_description": f"[{escalation_type}] Case {case_id}",
            "description": reason,
            "assignment_group": assigned_queue,
        },
    )
    return {"escalationId": resp.json()["result"]["number"], "state": "HUMAN_REVIEW", "slaHours": 4}

    # ── Option C: Jira ────────────────────────────────────────────────────────
    resp = requests.post(
        "https://<your-jira>/rest/api/3/issue",
        auth=("<email>", "<api-token>"),
        json={
            "fields": {
                "project": {"key": "BANK"},
                "summary": f"[{escalation_type}] Case {case_id}",
                "description": {"type": "doc", "version": 1,
                                "content": [{"type": "paragraph",
                                             "content": [{"type": "text", "text": reason}]}]},
                "issuetype": {"name": "Task"},
            }
        },
    )
    return {"escalationId": resp.json()["key"], "state": "HUMAN_REVIEW", "slaHours": 4}
```

### Durable circuit breaker

The circuit breaker in `guardrail_tools.py` uses an in-memory Python dict — safe for
development but does not persist across agent restarts. For production, replace
`_call_counts` with a Redis or CMS-backed store:

```python
import redis
_redis = redis.Redis(host="redis-service", port=6379, db=0)

def _get_count(case_id: str, agent: str) -> int:
    return int(_redis.hget(f"cb:{case_id}", agent) or 0)

def _increment(case_id: str, agent: str) -> int:
    return _redis.hincrby(f"cb:{case_id}", agent, 1)
```

---

## Step 9 — Promote to production (live environment)

Once draft tests pass, publish each agent to the live environment:

```bash
# Via CLI — publish each agent (repeat for all 12):
orchestrate agents publish --name case_supervisor_agent --environment live
orchestrate agents publish --name compliance_supervisor_agent --environment live
# ... (repeat for all 12 agents)

# Or via UI:
# <WXO_URL>/build → select agent → Publish → select "live" environment

# After publishing, run patch_max_tokens on live too:
python3 scripts/patch_max_tokens.py
```

> Connections must be configured for both `draft` and `live` environments before
> publishing. See Step 2 above for the live-environment `configure` and `set-credentials`
> commands.

---

## Step 10 — Observability

### View traces in the UI

```
<WXO_URL>/build/evaluate
```

Every agent invocation produces a trace showing:
- Which agent ran and which LLM was called
- Which tools were called with inputs and outputs
- Handoffs between agents (collaborator delegations)
- Guardrail verdicts (PASS / BLOCKED)
- Total latency and token usage per step

### Add Langfuse tracing (optional)

Enable in `config/env.yaml`:

```yaml
langfuse:
  enabled: true
  host: "https://cloud.langfuse.com"   # or your self-hosted URL
  public_key: "<from Langfuse project settings>"
  secret_key: "<from Langfuse project settings>"
  project_name: "banking-agents"
  environment: "production"
  redact_pii: true   # always true for banking — redacts PAN, Aadhaar, account numbers
```

> Self-hosted Langfuse is strongly recommended for production banking workloads to
> satisfy data residency requirements.

### Add your own audit logging

In `case_management_tools.py`, the `advance_case_state()` and `add_case_artifact()`
functions write to your Case Management System. Hook these into your bank's audit log:

```python
@tool
def advance_case_state(
    case_id: str,
    new_state: str,
    actor: str,
    remarks: str = "",
) -> dict:
    # Write to your audit database
    audit_log.write({
        "caseId": case_id,
        "newState": new_state,
        "actor": actor,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "remarks": remarks,
    })
    # Update the Case Management System
    cms_client.update_case(case_id, state=new_state)
    return {"caseId": case_id, "newState": new_state, "advancedAt": datetime.utcnow().isoformat()}
```

---

## Quick reference — agent names and roles

| Agent | Role |
|---|---|
| `case_supervisor_agent` | Primary — start here |
| `compliance_supervisor_agent` | AML + Sanctions + FEMA coordinator |
| `customer_360_agent` | Customer profile aggregator |
| `kyc_nri_agent` | KYC + NRI classification |
| `credit_bureau_agent` | CIBIL score retrieval |
| `credit_assessment_agent` | Policy eligibility (FOIR/DTI) |
| `document_agent` | Document AI — classify, extract, validate |
| `aml_agent` | AML transaction screening |
| `sanctions_agent` | OFAC/UN/EU/IN sanctions screening |
| `fema_remittance_agent` | FEMA/LRS eligibility |
| `fx_agent` | FX rate + locked quote |
| `payment_agent` | Beneficiary validation + payment |

> Run `python3 scripts/fetch_config.py` to get your IDs after deployment and populate `config/env.yaml`.

---

## Integration checklist

### Per backend system
- [ ] Replace tool stub with real API call
- [ ] Create Orchestrate Connection with correct `kind` (api_key / bearer / oauth)
- [ ] Configure connection for both `draft` and `live` environments
- [ ] Re-import tool with `--app-id` pointing to the connection
- [ ] Run smoke test via Preview panel
- [ ] Verify PII fields are not exposed in logs or traces

### For the full platform
- [ ] All 38 tools integrated and tested (9 Python files + 1 OpenAPI spec)
- [ ] `guardrail_tools.py` circuit breaker replaced with durable store
- [ ] Human task queue wired to `escalate_to_human()` in `case_management_tools.py`
- [ ] Case Management System wired to `advance_case_state()` and `add_case_artifact()`
- [ ] Audit log hooked into all state transitions
- [ ] Digital channel configured (webchat / REST / WhatsApp / Teams)
- [ ] Langfuse or equivalent observability enabled with PII redaction
- [ ] SLO targets in `slo/agent_slos.yaml` reviewed and approved by risk/compliance
- [ ] Eval suites pass (`python3 evals/run_evals.py`) — compliance suites at 100%
- [ ] End-to-end test with real customer data completed in UAT
- [ ] All agents promoted to live environment (`orchestrate agents publish`)
- [ ] `python3 scripts/patch_max_tokens.py` run against live environment
- [ ] Traces reviewed in Evaluate panel for each agent
