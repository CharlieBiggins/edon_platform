# EDON-AGENT-GATEWAY-001

This internal deterministic evaluation exercises the protocol-normalization,
custody, tenancy, replay, audit, healthcare read-only, telemetry-minimization,
and execution-authority boundaries of the EDON Agent Gateway.

Passing establishes only that the local reference controls behave as tested. It
does not establish live vendor interoperability, production security,
healthcare compliance, delivery reliability, real-institution validity, or
authorization for binding operation.

```bash
PYTHONPATH=src python evaluations/EDON-AGENT-GATEWAY-001/run_evaluation.py
```