# Transfer-007 failure audit protocol

`evidence/transfer007-observed-result.json` records only aggregate metrics from
the frozen Transfer-007 evaluation. `audit_transfer007.py` verifies that both
candidate gates failed, queue and pair exactness were zero, deferred-event
exactness was zero, and state reconstruction remained below 40%.

The audit is descriptive and non-authoritative. It cannot revise Transfer-007
or expose protected labels. Exact Transfer-007 cases are prohibited from
ActionNet-009 and DEV-009; repair data must use fresh semantic families,
lineages, domains, and renderers.