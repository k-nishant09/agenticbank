# Banking Agentic Platform — Integration Guide

**How to connect the 12 deployed agents to your enterprise banking systems.**

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

> After deploying, run `orchestrate agents list` to get your agent IDs, then
> populate `config/env.yaml` under the `agents:` section.

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

---

## Step 2 — Add API credentials as Orchestrate Connections

Never hardcode secrets in tool files. Use Orchestrate Connections to inject credentials.

### Create a connection for each backend system

```bash
# Example: create a connection for the CIBIL API
uvx --from ibm-watsonx-orchestrate orchestrate connections create \
  --app-id cibil-api-connection

# Set credentials (API key)
uvx --from ibm-watsonx-orchestrate orchestrate connections configure \
  --app-id cibil-api-connection \
  --environment draft \
  --type team \
  --kind api_key

uvx --from ibm-watsonx-orchestrate orchestrate connections set-credentials \
  --app-id cibil-api-connection \
  --environment draft \
  --api-key "<your-cibil-api-key>"
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
        f"https://api.cibil.com/v2/scores",
        params={"customerId": customer_id, "pan": pan_number},
        headers={"X-API-Key": api_key},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()
```

---

## Step 3 — Re-import updated tools

After replacing stubs with real API calls:

```bash
cd orchestrate-project

# Re-import each tool file (update in-place)
uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/customer_360_tools.py

uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/kyc_tools.py

uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/credit_bureau_tools.py

uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/credit_assessment_tools.py

uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/document_tools.py

uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/compliance_tools.py

uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/fx_payment_tools.py

uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/case_management_tools.py
```

---

## Step 4 — Connect tools to agents via app_id

Link each tool to its credential connection when re-importing:

```bash
uvx --from ibm-watsonx-orchestrate orchestrate tools import -k python \
  tools/python/credit_bureau_tools.py \
  --app-id cibil-api-connection
```

---

## Step 5 — Import the Core Banking OpenAPI tool

The OpenAPI spec at `tools/openapi/core-banking-api.yaml` defines the CBS API.
Replace the `servers.url` field with your actual CBS API Gateway URL, then import:

```bash
# Edit the spec first
nano tools/openapi/core-banking-api.yaml
# Change: url: https://api.bank.internal/cbs/v1
# To:     url: https://<your-actual-api-gateway>/cbs/v1

# Import with connection
uvx --from ibm-watsonx-orchestrate orchestrate tools import -k openapi \
  tools/openapi/core-banking-api.yaml \
  --app-id crm-api-connection
```

Then add the CBS tools (`getAccount`, `getCustomerAccounts`, `getCustomerLoans`) to
`customer_360_agent` via the UI or by updating the agent YAML and re-importing.

---

## Step 6 — Test the agent chain end-to-end

Open the supervisor agent in the UI:

```
<your-wxo-url>/build
# Click case_supervisor_agent → Preview
```

### Smoke test messages (use the Preview panel)

**Test 1 — Loan eligibility**
```
I need a ₹75 lakh personal loan. My customer ID is C001.
```
Expected path: `case_supervisor` → `customer_360_agent` → `kyc_nri_agent` → `credit_bureau_agent` → `credit_assessment_agent`

**Test 2 — Full NRI journey**
```
I need a ₹75L loan and want to transfer ₹20 lakh to my Singapore account after approval.
```
Expected path: full 14-step flow → human approval gate → FX quote → payment

**Test 3 — Compliance block**
```
I need a ₹75L loan. My customer ID is C999. Transfer ₹20L to beneficiary John Doe in Iran.
```
Expected path: `sanctions_agent` → STOP → escalate to human

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
import requests

BASE     = "<your-wxo-url>"                  # from config/env.yaml wxo.url
AGENT_ID = "<case_supervisor_agent-id>"      # from: orchestrate agents list
TOKEN    = "<your-api-key-or-session-token>" # from: ./scripts/login.sh

# Start a conversation run
r = requests.post(
    f"{BASE}/v1/orchestrate/runs",
    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    json={"message": {"role": "user", "content": "I need a ₹75 lakh personal loan."},
          "agent_id": AGENT_ID},
    verify=False   # set to True in production with valid TLS
)
run_id = r.json()["run_id"]
# Poll GET /v1/orchestrate/runs/{run_id} until status == "completed"
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

---

## Step 8 — Set up human-in-the-loop

The agents call `escalate_to_human()` at three gates:
1. **Credit review** — borderline FOIR, MANUAL_REVIEW_REQUIRED
2. **Compliance review** — AML / Sanctions flag
3. **Payment authorization** — high-value payment gate

### Wire escalation to your task queue

Replace the stub in `case_management_tools.py` `escalate_to_human()` with a call to your
human task system (ServiceNow, Jira, or Orchestrate's built-in task manager):

```python
@tool
def escalate_to_human(case_id: str, reason: str, escalation_type: str, assigned_queue: str) -> dict:
    # Option A: Orchestrate built-in human task
    from ibm_watsonx_orchestrate.agent_builder.tools import create_human_task
    task = create_human_task(
        title=f"Case {case_id} — {escalation_type}",
        description=reason,
        assignee_queue=assigned_queue,
    )
    return {"escalationId": task.id, "state": "HUMAN_REVIEW", "slaHours": 4}

    # Option B: ServiceNow
    resp = requests.post(
        "https://<your-snow>.service-now.com/api/now/table/incident",
        auth=("<user>", "<pass>"),
        json={"short_description": f"[{escalation_type}] Case {case_id}", "description": reason},
    )
    return {"escalationId": resp.json()["result"]["number"], "state": "HUMAN_REVIEW"}
```

---

## Step 9 — Promote to production (live environment)

Once draft tests pass:

```bash
# Publish each agent via the UI:
#   <WXO_URL>/build → agent → Publish → select "live" environment
#
# Or via CLI (replace <agent-name> with each agent name):
orchestrate agents publish --name case_supervisor_agent --environment live
```

---

## Step 10 — Observability

### View traces in the UI

```
<WXO_URL>/build/evaluate
```

Every agent invocation produces a trace showing:
- Which agent ran
- Which tools were called
- Tool inputs and outputs
- Handoffs between agents
- Total latency and token usage

### Add your own audit logging

In `case_management_tools.py`, the `advance_case_state()` and `add_case_artifact()` functions
write to your Case Management System. Hook these into your bank's audit log:

```python
@tool
def advance_case_state(case_id: str, new_state: str, actor: str, remarks: str = "") -> dict:
    # Write to your audit database
    audit_log.write({
        "caseId": case_id,
        "newState": new_state,
        "actor": actor,
        "timestamp": datetime.utcnow().isoformat(),
        "remarks": remarks,
    })
    # Update the Case Management System
    cms_client.update_case(case_id, state=new_state)
    return {"caseId": case_id, "newState": new_state, ...}
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

> Run `orchestrate agents list` to get your IDs after deployment.

---

## Integration checklist

### For each backend system
- [ ] Replace tool stub with real API call
- [ ] Create Orchestrate Connection with credentials
- [ ] Re-import tool with `--app-id` pointing to the connection
- [ ] Run smoke test via Preview panel

### For the full journey
- [ ] All 31 tools integrated and tested
- [ ] Human task queue wired to `escalate_to_human()`
- [ ] Case Management System wired to `advance_case_state()`
- [ ] Audit log wired to all state transitions
- [ ] Digital channel (webchat / REST / WhatsApp) configured
- [ ] Traces reviewed in Evaluate panel
- [ ] End-to-end test with real customer data (in UAT)
- [ ] Promoted to live environment
