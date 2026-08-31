# Prompt Management

Externalized, versioned system prompts for every agent in the platform.

## Why this matters

Every production case records the agent version + prompt version (see `case_management_tools.py`
audit trail). Six months later, if a regulator asks "why did this customer's loan case
proceed to payment?", you can reconstruct the exact prompt that governed the decision.

## Structure

```
prompts/
├── README.md
├── PROMPT_REGISTRY.yaml           ← index: owner, version, eval_score, approval status
│
├── supervisor/
│   ├── v1.md                      ← original prompt (immutable once deployed)
│   └── v2.md                      ← current production prompt
│
├── customer/
│   └── v1.md
│
├── credit/
│   ├── v1.md
│   └── v2.md
│
├── compliance/
│   └── v1.md
│
├── payment/
│   └── v1.md
│
├── kyc/
│   └── v1.md
│
├── document/
│   └── v1.md
│
└── fx/
    └── v1.md
```

## Versioning rules

1. **Never edit a deployed prompt file** — create a new version file (`v2.md`, `v3.md`).
2. A new prompt version must pass the eval suite before being deployed (`evals/run_evals.py`).
3. Each version has an entry in `PROMPT_REGISTRY.yaml` with approval status.
4. The active version is referenced in the agent YAML (`prompt_version:` field).
5. When a prompt is promoted to production, update `PROMPT_REGISTRY.yaml` and the agent YAML.

## Prompt metadata header

Every prompt file starts with a YAML front-matter block:

```yaml
---
agent: case_supervisor_agent
version: v2
author: <email>
effective_date: 2026-07-15
change_reason: "Added guardrail tool calls per control-plane design"
eval_score: 97.2%
approved_by: <name>
replaces: v1
---
```
