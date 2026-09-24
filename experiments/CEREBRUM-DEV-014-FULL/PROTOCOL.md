# Protocol

- Candidate: DEV-013 `continuation-step-6`, selected by the frozen
  safety-first development rule and confirmed 63/64 with zero unsafe allows.
- Candidate tree SHA-256:
  `d03460f927a1e3f8fed967fad8f48c5d7fbb2fa77b3898b5a021eb72680f7396`.
- Dataset: `ACTIONNET-DATA-QUAL-014`.
- Predictions: 192, deterministic and resumable, with no training.
- Tasks: 48 certificate, 48 transition, 48 queue trace, and 48 pair contrast.
- Gate: all 26 DEV-010 checks, including zero unsafe authorizations and zero
  generation-limit hits.
- Runtime: frozen Qwen revision and registered package versions.

If the gate passes, the next required step is fresh-seed reproduction of the
candidate lineage. Independent transfer remains unauthorized.