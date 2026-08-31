# Agent Evaluation Datasets

Per-agent labeled evaluation cases used to gate deployments.

## Structure

```
evals/
├── README.md
├── run_evals.py                        ← eval runner (gates deploy.sh)
│
├── credit_assessment/
│   ├── cases.jsonl                     ← labeled input cases
│   └── expected.jsonl                  ← expected outputs and metrics
│
├── compliance/
│   ├── aml_adversarial.jsonl
│   ├── sanctions_near_name.jsonl
│   └── fema_limit_boundary.jsonl
│
└── supervisor/
    └── routing_accuracy.jsonl
```

## Running evals

```bash
# Run all evals — used as deploy gate
python3 evals/run_evals.py

# Run a single suite
python3 evals/run_evals.py --suite credit_assessment
python3 evals/run_evals.py --suite compliance
python3 evals/run_evals.py --suite supervisor

# Verbose output (show each case result)
python3 evals/run_evals.py --verbose
```

## Pass thresholds (from SLO definitions in slo/)

| Suite              | Metric                  | Minimum threshold |
|--------------------|-------------------------|-------------------|
| credit_assessment  | Decision agreement      | ≥ 95%             |
| credit_assessment  | Policy adherence        | = 100%            |
| compliance/aml     | False negative rate     | = 0%              |
| compliance/sanctions| False negative rate    | = 0%              |
| compliance/fema    | Limit enforcement       | = 100%            |
| supervisor/routing | Routing accuracy        | ≥ 95%             |
| supervisor/routing | Wrong-agent rate        | < 2%              |

## Adding cases

Each `.jsonl` file has one JSON object per line:

```json
{"id": "case-001", "input": {...}, "expected_output": {...}, "tags": ["boundary", "cibil"]}
```

For compliance evals, every false-negative is a **critical failure** — deployment
is blocked even if only one case fails (false_negative_rate must be exactly 0%).
