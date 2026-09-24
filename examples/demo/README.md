# End-to-end synthetic institution demo

The demo exercises the complete internal control flow:

```text
Compiler → Review Registry → Promotion → IR Runtime → ActionNet
         → Qualification → Seed Orchestration → Shadow → Gap Discovery
```

Run it outside the repository artifact tree:

```bash
PYTHONPATH=src python examples/demo/run_demo.py --output-dir /tmp/edon-demo
```

The seed workers and predictions in this demo are oracle-derived plumbing
diagnostics. They are explicitly not learned Cerebrum results.