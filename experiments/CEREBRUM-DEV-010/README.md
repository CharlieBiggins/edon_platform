# CEREBRUM-DEV-010

Fresh two-seed learned-development successor to the frozen
`CEREBRUM-DEV-009-RB1` negative result.

The campaign trains Qwen3-4B QLoRA on 4,032
`ACTIONNET-DATA-QUAL-010` records. It retains the four scored EventNet tasks and
adds decomposed queue-order and queue-partition supervision. Validation uses
192 fresh held-renderer records and excludes every RB1 lineage and case.

Status: `DEV010_REPAIR_NOT_ESTABLISHED` from the operator-reported September 5,
2026 execution. Seed 26090401 passed all 26 gates. Seed 26090402 passed 24/26,
scored 0/2 on unresolved-appeal certificates, and produced one unsafe `ALLOW`
in that family. The two-seed summary therefore passed 4/6 checks. Raw GPU
artifacts remain under external Volume custody; the repository preserves the
reported result in `evidence/operator-reported-result-2026-09-05.json`.

The additive `CEREBRUM-DEV-011-FOCUSED` successor continues both frozen
adapters on fresh appeal-boundary data. Transfer-010 remains locked.

Run:

```bash
python preflight.py
python train.py --seed 26090401
python predict.py --seed 26090401
python train.py --seed 26090402
python predict.py --seed 26090402
python score.py
```
