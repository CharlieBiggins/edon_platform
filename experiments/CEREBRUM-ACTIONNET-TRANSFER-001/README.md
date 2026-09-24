# ActionNet Transfer-001 — protected successor shell

Status: `BLOCKED_PROTECTED_SHELL_NO_INSTRUMENT`.

This package reserves the proposed smallest independent transfer study: three
unseen synthetic institutions, 16 cases and eight counterfactual pairs per
institution, answered by all four frozen Matched candidates (192 responses).

It deliberately contains **no institution, prompt, label, generator seed,
oracle answer or scoring result**. EDON cannot truthfully create its own
“independent” test and ship it beside the candidates. A named independent author
and separate custody commitments must fill `custody.template.json`; both
ActionNet seeds must already pass Matched-002.

The custodian package must contain:

- `metadata.json` with exactly three institution IDs and authorship declarations;
- `inputs.jsonl` with 48 label-free shared-interface prompts;
- `reference.jsonl` with the aligned hidden executable references;
- 24 complete counterfactual pairs, eight inside each institution;
- frozen hashes committed before candidate inference.

Run `python -B .../run.py preflight` locally. Only the protected custodian should
run `validate-package` and `register`. Candidate inference uses only the copied
label-free inputs; the scoring custodian later runs `score` with the still-hidden
reference. A passing validation says the package shape is correct, not that
independence, transfer or safety has been proven.