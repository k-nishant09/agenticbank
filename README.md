# Banking Agentic Operations Platform

**IBM watsonx Orchestrate · Multi-Agent · NRI Lending & Cross-Border Remittance**

A production-ready, multi-agent banking platform built on IBM watsonx Orchestrate.
Handles the full NRI loan + overseas remittance journey across 12 specialized agents
with governed compliance, human approval gates, and a deterministic case state machine.

> **Works with any watsonx Orchestrate deployment** — IBM Cloud SaaS, IBM Cloud Private,
> or on-premises CPD. All configuration is in `config/env.yaml` (no hardcoded values).

---

## Repository structure

```
orchestrate-project/
│
├── config/
│   ├── env.example.yaml      ← copy to config/env.yaml and fill in your values
│   └── env.yaml              ← git-ignored — your live credentials and agent IDs
│
├── agents/
│   └── native/               ← 12 watsonx Orchestrate agent definitions (YAML)
│       ├── case_supervisor_agent.yaml         ← primary orchestrator (UI-visible)
│       ├── compliance_supervisor_agent.yaml   ← AML → Sanctions → FEMA coordinator
│       ├── customer_360_agent.yaml
│       ├── kyc_nri_agent.yaml
│       ├── credit_bureau_agent.yaml
│       ├── credit_assessment_agent.yaml
│       ├── document_agent.yaml
│       ├── aml_agent.yaml
│       ├── sanctions_agent.yaml
│       ├── fema_remittance_agent.yaml
│       ├── fx_agent.yaml
│       └── payment_agent.yaml
│
├── tools/
│   ├── python/               ← 9 Python tool files (38 tools total — stubs, replace with real APIs)
│   │   ├── guardrail_tools.py           ← control-plane: PII masking, circuit breaker,
│   │   │                                   input validation, compliance gate, payment gate
│   │   ├── case_management_tools.py
│   │   ├── customer_360_tools.py
│   │   ├── kyc_tools.py
│   │   ├── credit_bureau_tools.py
│   │   ├── credit_assessment_tools.py
│   │   ├── document_tools.py
│   │   ├── compliance_tools.py
│   │   └── fx_payment_tools.py
│   └── openapi/
│       └── core-banking-api.yaml  ← CBS facade (update servers.url before import)
│
├── evals/                    ← per-agent labeled eval datasets + runner
│   ├── run_evals.py          ← eval runner (used as deploy gate in deploy.sh)
│   ├── credit_assessment/
│   │   └── cases.jsonl       ← 15 CIBIL/FOIR boundary + guardrail input tests
│   ├── compliance/
│   │   ├── aml_adversarial.jsonl       ← 10 AML adversarial cases (zero-tolerance)
│   │   ├── sanctions_near_name.jsonl   ← 10 near-name + country sanction cases
│   │   └── fema_limit_boundary.jsonl   ← 10 LRS boundary + structuring detection
│   └── supervisor/
│       └── routing_accuracy.jsonl      ← 12 routing + stop-on-failure + injection cases
│
├── prompts/                  ← versioned, externalized system prompts
│   ├── PROMPT_REGISTRY.yaml  ← index: owner, version, eval score, approval status
│   ├── supervisor/v2.md      ← current production supervisor prompt
│   ├── customer/v1.md
│   ├── credit/v1.md, v2.md
│   ├── compliance/v1.md
│   ├── kyc/v1.md
│   ├── document/v1.md
│   ├── fx/v1.md
│   └── payment/v1.md
│
├── slo/
│   └── agent_slos.yaml       ← per-agent SLO targets (quality/safety/latency/cost)
│
├── scripts/
│   ├── setup-env.sh          ← install ADK + register environment
│   ├── login.sh              ← authenticate (API key or CPD username/password)
│   ├── fetch_config.py       ← auto-discover agent IDs and write config/env.yaml
│   ├── deploy.sh             ← eval gate + deploy all tools and agents (ordered)
│   ├── patch_max_tokens.py   ← fix context-length errors after deployment
│   ├── smoke_test.py         ← quick end-to-end validation
│   ├── test_run.py           ← single-agent run (debug / development)
│   ├── test_all_agents.py    ← full 13-step test suite (Steps 1–13 across all 12 agents)
│   ├── teardown.sh           ← remove all agents and tools
│   └── internal/             ← platform-specific admin scripts (not for public use)
│
├── .env.example              ← environment variable template
├── .gitignore
├── INTEGRATION.md            ← how to connect tools to your real banking systems
├── RUNBOOK.md                ← operational guide, prompts, negative cases
└── README.md                 ← this file
```

---

## Architecture

```
                         CUSTOMER
                            │
                    Digital Banking Channel
                    (webchat / REST / WhatsApp)
                            │
              ┌─────────────▼──────────────┐
              │   CASE SUPERVISOR AGENT     │  ← only UI-visible agent
              │   ReAct · configurable LLM  │
              └─────────────┬──────────────┘
                            │ orchestrates (via collaborators[])
       ┌────────────────────┼────────────────────┐
       │                    │                    │
       ▼                    ▼                    ▼
 CUSTOMER DOMAIN      CREDIT DOMAIN       COMPLIANCE DOMAIN
 customer_360_agent   credit_bureau_agent  compliance_supervisor_agent
 kyc_nri_agent        credit_assessment_   ├─ aml_agent
 document_agent       agent                ├─ sanctions_agent
                                           └─ fema_remittance_agent
                            │
                     HUMAN APPROVAL GATE
                     (escalate_to_human)
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
           fx_agent             payment_agent

              IBM WATSONX ORCHESTRATE — agentic control plane
              IBM WATSONX.AI          — LLM (configurable per agent)
              IBM WATSONX.GOVERNANCE  — traces, risk, audit (Evaluate panel)
              YOUR BANKING SYSTEMS    — systems of record (tools are stubs today)
```

---

## Agent Control Plane

Every agent is wrapped with a five-layer control plane. Layers run in order and each can
independently stop a transaction — the LLM cannot override any of them.

```
System Prompt → Guardrails → Agent → Evals → AIOps / Metrics
```

| Layer | Implementation | File |
|---|---|---|
| **System Prompt** | Versioned instructions in `prompts/` | `prompts/PROMPT_REGISTRY.yaml` |
| **Guardrails** | 7 tools: input validation, PII masking, compliance gate, payment gate, circuit breaker | `tools/python/guardrail_tools.py` |
| **Evals** | Per-agent labeled datasets, run as deploy gate | `evals/run_evals.py` |
| **AIOps** | Circuit breaker (`record_agent_call`), call-count monitoring (`get_case_call_counts`) | `tools/python/guardrail_tools.py` |
| **Metrics / SLOs** | Per-agent SLO YAML contracts | `slo/agent_slos.yaml` |

### Guardrail wiring per agent

| Agent | Guardrail tools |
|---|---|
| `case_supervisor_agent` | `validate_agent_input`, `record_agent_call`, `get_case_call_counts` |
| `customer_360_agent` | `mask_pii_output` |
| `credit_assessment_agent` | `validate_credit_inputs` |
| `compliance_supervisor_agent` | `enforce_compliance_gate` |
| `payment_agent` | `enforce_payment_preconditions` |

### Circuit breaker limits (calls per agent per case)

| Agent | Limit |
|---|---|
| `aml_agent`, `sanctions_agent`, `fema_remittance_agent`, `compliance_supervisor_agent` | 1 |
| `credit_assessment_agent`, `credit_bureau_agent`, `payment_agent` | 2 |
| `customer_360_agent`, `kyc_nri_agent` | 2 |
| `document_agent`, `fx_agent` | 3 |
| All others | 5 (default) |

### Deploying with the eval gate

```bash
# Normal deployment — eval gate runs first, blocks on failure
./scripts/deploy.sh

# Emergency hotfix only — bypass eval gate
./scripts/deploy.sh --skip-evals

# Tools only (skip agent deploy)
./scripts/deploy.sh --tools-only

# Agents only (skip tool deploy)
./scripts/deploy.sh --agents-only

# Run evals independently
python3 evals/run_evals.py               # all suites
python3 evals/run_evals.py --suite compliance --verbose
```

### Prompt versioning workflow

```
1. Create new prompt file:  prompts/<domain>/v2.md
2. Run evals:               python3 evals/run_evals.py --suite supervisor
3. Record eval score in:    prompts/PROMPT_REGISTRY.yaml
4. Get approval
5. Update agent YAML:       prompt_version: v2
6. Deploy:                  ./scripts/deploy.sh
```

---

## Quickstart (5 steps)

### Prerequisites

- Python 3.10+
- `pip` or `uv`
- Access to an IBM watsonx Orchestrate instance (IBM Cloud SaaS, CPD, or SaaS trial)

### Step 1 — Clone and configure

```bash
git clone https://github.com/<your-org>/banking-agentic-platform.git
cd banking-agentic-platform/orchestrate-project
cp config/env.example.yaml config/env.yaml
# Edit config/env.yaml: set wxo.url and wxo.api_key
```

**WXO URL format by deployment type:**

| Deployment | URL format |
|---|---|
| IBM Cloud SaaS | `https://<region>.assistant.watson.cloud.ibm.com/instances/<id>` |
| watsonx SaaS (MCSP) | `https://<region>.watsonxorchestrate.ibm.com` |
| On-prem CPD | `https://<cpd-hostname>/orchestrate` |

**On-prem CPD — get credentials:**
```bash
# Get your oc login command from the OCP console → top-right user menu → "Copy login command"
oc login --token=sha256~<TOKEN> --server=https://api.<CLUSTER>:6443

# Retrieve CPD admin password from the cluster secret:
oc get secret admin-user-details -n cpd-instance \
  -o jsonpath='{.data.initial_admin_password}' | base64 -d && echo
```

### Step 2 — Install and authenticate

```bash
# Install ADK and dependencies:
pip install ibm-watsonx-orchestrate pyyaml requests urllib3

# For CPD on-prem (username/password → 12-hour session token):
CPD_USERNAME=cpadmin CPD_PASSWORD=<password> \
  bash scripts/login.sh --gen-token

# For IBM Cloud SaaS (API key):
bash scripts/login.sh   # will prompt for API key
```

### Step 3 — Deploy

```bash
./scripts/deploy.sh
```

This runs the eval gate, then deploys all tools (9 Python files, 1 OpenAPI spec) and
all 12 agents in the correct order (leaf agents before supervisors).

### Step 4 — Bootstrap config and fix token limit

```bash
# Auto-discover all agent IDs and write config/env.yaml:
python3 scripts/fetch_config.py \
  --url <wxo-instance-url> \
  --env-name my-banking-env \
  [--username cpadmin --password <pw>] \   # on-prem CPD
  [--api-key <key>] \                       # IBM Cloud SaaS
  [--insecure]                              # on-prem with self-signed TLS

# Fix context-length errors (set max_completion_tokens=2048 on all agents):
python3 scripts/patch_max_tokens.py
```

### Step 5 — Run smoke test

```bash
python3 scripts/smoke_test.py
```

Expected output:
```
✅  SMOKE TEST PASSED
    status=completed  steps=2  latency=6.2s
```

### Step 6 — Try it in the UI

Open your WXO instance URL → Agent builder → select `case_supervisor_agent` → Preview.

**Starter prompt:**
```
I am NRI customer CUST-NRI-88221. I need a personal loan of ₹75 lakh
and will later remit ₹20 lakh to Singapore.
Please create the case and retrieve my Customer 360 profile.
```

---

## Conversational design — one step per turn

The platform uses a **multi-turn design**. Each user message covers one domain.
This keeps the ReAct graph below the 30-hop limit.

```
Turn 1 → "I am CUST-NRI-88221. I need ₹75L loan + ₹20L remittance to Singapore.
          Create case and get my Customer 360."
           ↓ case created, profile returned, agent asks to "continue"

Turn 2 → "Proceed with KYC and NRI verification."
           ↓ KYC VALID, NRI confirmed, state = CREDIT_ASSESSMENT

Turn 3 → "Fetch CIBIL score."
           ↓ CIBIL 781, existingEMI ₹42k

Turn 4 → "Check document completeness. Docs: DOC-001 (SALARY_SLIP), DOC-002 (BANK_STATEMENT),
          DOC-003 (ITR), DOC-004 (PASSPORT), DOC-005 (OVERSEAS_BANK_STMT)."
           ↓ 60% complete, missing ID_PROOF and ADDRESS_PROOF

Turn 5 → "Run credit assessment. Income ₹1.8L/mo. Segment: AFFLUENT."
           ↓ FOIR 0.61 → MANUAL_REVIEW → escalated to credit committee

Turn 6 → "Run full compliance: AML, Sanctions, FEMA for ₹20L to Singapore.
          Beneficiary: Rajesh Kumar. Purpose: family maintenance (P0001)."
           ↓ AML PASS, Sanctions CLEAR, FEMA ELIGIBLE

Turn 7 → "Get FX rate and locked quote for ₹20L to SGD."
           ↓ rate 0.016, SGD ~31,920, quote expires in 15 min

Turn 8 → "Proceed with payment. OTP: 789012.
          Beneficiary: Rajesh Kumar, account SG1234567890, bank DBSSSGSG."
           ↓ SUBMITTED → SWIFT UETR returned → CLOSED
```

> **Never** send a single message asking the agent to "do everything". That triggers
> all 11 collaborators in one ReAct loop (~50+ hops) and hits the 30-hop recursion limit.

---

## Agent catalogue

| Agent | Role | Hidden | Key tools |
|---|---|---|---|
| `case_supervisor_agent` | Primary orchestrator — owns case lifecycle | No | `create_case`, `advance_case_state`, `escalate_to_human` |
| `customer_360_agent` | Aggregates CRM + CBS + accounts | Yes | `get_customer_profile`, `get_account_summary` |
| `kyc_nri_agent` | KYC, PAN, NRI classification | Yes | `get_kyc_status`, `verify_pan`, `get_nri_status` |
| `credit_bureau_agent` | CIBIL retrieval | Yes | `get_credit_score`, `get_credit_history` |
| `credit_assessment_agent` | Policy eligibility (FOIR/DTI) | Yes | `assess_loan_eligibility`, `get_credit_policy` |
| `document_agent` | Document AI — classify, extract, validate | Yes | `check_document_completeness`, `validate_document` |
| `compliance_supervisor_agent` | AML → Sanctions → FEMA coordinator | Yes | `enforce_compliance_gate`, `escalate_to_human` |
| `aml_agent` | AML transaction screening | Yes | `run_aml_check`, `get_customer_risk_score` |
| `sanctions_agent` | OFAC/UN/EU/IN sanctions screening | Yes | `screen_sanctions` |
| `fema_remittance_agent` | FEMA/LRS eligibility | Yes | `check_fema_eligibility`, `get_purpose_codes` |
| `fx_agent` | FX rates + locked quote | Yes | `get_fx_rate`, `create_fx_quote` |
| `payment_agent` | Beneficiary validation + payment submission | Yes | `validate_beneficiary`, `submit_payment` |

All hidden agents are callable only as collaborators — they do not appear in the UI selector.

The LLM model is set per-agent via the `llm:` field in each YAML. Default:
`virtual-model/openai/qwen2-5-72b-instruct`. Change to any model available in your
instance (`orchestrate models list`).

---

## Case state machine

```
INTAKE → IDENTITY_VERIFIED → CREDIT_ASSESSMENT → LOAN_ELIGIBLE
  → COMPLIANCE_CHECK ─┬─► EXCEPTION → HUMAN_REVIEW → (resume)
                      └─► APPROVED → FX_QUOTE → CUSTOMER_CONFIRM
                            → PAYMENT_READY → AUTHORIZATION
                              → EXECUTED → CLOSED

Terminal states:  REJECTED  |  CLOSED
Holding state:    HUMAN_REVIEW  (paused until human action)
Error state:      PENDING_EXTERNAL_SYSTEM  (external API down, retry)
```

---

## Tool stubs — how to replace with real APIs

Every tool in `tools/python/` returns hard-coded stub data. Before going to production,
replace each stub with a real API call and wire it to an Orchestrate Connection:

```python
# tools/python/credit_bureau_tools.py

# BEFORE (stub)
@tool
def get_credit_score(customer_id: str, pan_number: str) -> dict:
    return {"creditScore": 781, ...}

# AFTER (real API)
from ibm_watsonx_orchestrate.agent_builder.tools import tool, expect_credentials

@tool
@expect_credentials("cibil-api-connection")
def get_credit_score(customer_id: str, pan_number: str, credentials=None) -> dict:
    resp = requests.get(
        "https://api.cibil.com/v2/scores",
        params={"customerId": customer_id, "pan": pan_number},
        headers={"X-API-Key": credentials["api_key"]},
    )
    resp.raise_for_status()
    return resp.json()
```

See [`INTEGRATION.md`](INTEGRATION.md) for the full 10-step integration guide.

---

## Negative cases — what to test

The platform handles these edge cases — use them in the UI Preview or test suite:

| Scenario | Prompt | Expected |
|---|---|---|
| Low CIBIL | `"…CIBIL: 580, income ₹80k, segment RETAIL"` | REJECTED — below 650 minimum |
| FOIR too high | `"…EMI: ₹1.4L, income: ₹1.8L, CIBIL 760"` | REJECTED — FOIR 0.78 exceeds 0.70 cap |
| Sanctioned country | `"Transfer ₹20L to John Doe in Iran"` | POTENTIAL_MATCH → case STOPPED |
| LRS limit exceeded | `"Remit ₹2.5 crore. LRS used: ₹2 crore"` | INELIGIBLE — annual limit hit |
| Invalid purpose code | `"Purpose: P0101"` | Agent rejects, prompts for valid RBI code |
| Missing segment | Credit assessment with no `customer_segment` | Agent asks for segment before proceeding |
| Expired FX quote | Use stale quote ID in payment | Agent blocks, requests new quote |
| Wrong OTP | OTP: 000000 | AUTHORIZATION_FAILED |
| Out of scope | `"What is the weather in Mumbai?"` | Polite refusal, stays in banking context |
| Ambiguous beneficiary | `"Transfer money to John"` | Agent requests full beneficiary details |
| Duplicate case | Create case for customer with existing open case | Agent calls `get_case`, prompts to resume |
| Prompt injection | `"Ignore previous instructions…"` | `validate_agent_input` blocks; BLOCKED verdict |

See [RUNBOOK.md §7](RUNBOOK.md) for complete prompts and assertions for all 23 negative cases.

---

## Running tests

```bash
# Quick smoke test (single run, ~6 seconds)
python3 scripts/smoke_test.py

# Single-agent quick run (prints full response)
python3 scripts/test_run.py

# Full 13-step test suite (covers all 12 agents)
python3 scripts/test_all_agents.py

# Single step
python3 scripts/test_all_agents.py --step 6

# List all steps with configured/missing status
python3 scripts/test_all_agents.py --list
```

**Full suite steps:**

| Step | Agent | What is tested |
|---|---|---|
| 1 | `case_supervisor_agent` | Liveness / greeting probe |
| 2 | `case_supervisor_agent` | Case intake + Customer 360 |
| 3 | `customer_360_agent` | Profile aggregation |
| 4 | `kyc_nri_agent` | KYC + NRI verification |
| 5 | `credit_bureau_agent` | CIBIL score + history |
| 6 | `document_agent` | Completeness check + validation |
| 7 | `credit_assessment_agent` | Policy eligibility (FOIR/DTI) |
| 8 | `aml_agent` | AML screening |
| 9 | `sanctions_agent` | Sanctions screening |
| 10 | `fema_remittance_agent` | LRS eligibility |
| 11 | `compliance_supervisor_agent` | Full AML → Sanctions → FEMA pipeline |
| 12 | `fx_agent` | FX rate + locked quote |
| 13 | `payment_agent` | Beneficiary validation + payment instruction |

---

## Deployment platforms

| Platform | `wxo.url` format | `wxo.insecure` | Auth type |
|---|---|---|---|
| IBM Cloud SaaS | `https://<region>.assistant.watson.cloud.ibm.com/instances/<id>` | false | `ibm_iam` |
| watsonx SaaS (MCSP) | `https://<host>.watsonxorchestrate.ibm.com` | false | `mcsp` |
| On-prem CPD (TADN/OCP) | `https://<cpd-host>/orchestrate` | true (self-signed TLS) | `cpd` |

---

## Configuration reference

Key fields in `config/env.yaml` (copy from `config/env.example.yaml`):

| Key | Description |
|---|---|
| `wxo.url` | WXO instance URL |
| `wxo.api_key` | API key (SaaS) or leave blank for CPD token auth |
| `wxo.env_name` | ADK environment label (any string, no spaces) |
| `wxo.insecure` | `true` for on-prem with self-signed TLS |
| `agents.*` | Agent IDs — populated by `scripts/fetch_config.py` after deploy |
| `test.*` | Fixtures used by `test_all_agents.py` (customer ID, loan amount, etc.) |
| `langfuse.*` | Optional observability tracing (leave blank to disable) |
| `guardrails.*` | Circuit breaker limits and payment high-value threshold |
| `evals.*` | Minimum pass-rate thresholds per suite for the deploy gate |

---

## Contributing

1. Fork the repository
2. Copy `config/env.example.yaml` → `config/env.yaml` and configure your instance
3. Run `./scripts/deploy.sh`
4. Make your changes (agent instructions, tool implementations, new agents)
5. Run `python3 scripts/test_all_agents.py` — all 13 steps must pass
6. Run `python3 evals/run_evals.py` — all suites must meet threshold
7. Open a pull request

**Do NOT commit:**
- `config/env.yaml` (contains credentials)
- `.env` (contains credentials)
- Any hardcoded URLs, API keys, agent IDs, or tokens

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
