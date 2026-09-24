# Architecture governance

This directory records additive architecture migrations that must not rewrite
historical experimental evidence. Migrations define terminology, compatibility,
and claim boundaries; they do not create scientific results.

Current records:

- `cerebrum-c1-migration.json` — additive C1/Cerebrum System terminology and
  compatibility boundary effective 2026-08-30.
- `CEREBRUM-PLATFORM-VISION-001/` — frozen predecessor effective 2026-09-20.
  It remains immutable historical architecture governance.
- `cerebrum-platform-vision-001-to-002.json` — additive successor migration;
  Vision-001 is not rewritten.
- `CEREBRUM-PLATFORM-VISION-002/` — controlling successor effective
  2026-09-21, adding the Institutional Control Graph, delegated authority and
  commitments, and receipt model. It is not an implementation or scientific
  result.
- `CEREBRUM-MATURE-PLATFORM-SPEC-001/` — controlling product and technical-
  contract specification effective 2026-09-22. It inherits Vision-002, defines
  eleven canonical specifications, and creates no implementation or capability
  result.
- `CEREBRUM-PLATFORM-FOUNDATION-001/` — vendor-neutral implementation draft
  registered 2026-09-23. It defines operational trust boundaries and freeze
  gates but is not deployment authorization or an implementation result.
- `CEREBRUM-AWS-DEPLOYMENT-PROFILE-001/` — replaceable AWS reference mapping
  registered 2026-09-23. It remains unqualified and creates no infrastructure,
  compliance, cost, customer, production, or write-authority claim.