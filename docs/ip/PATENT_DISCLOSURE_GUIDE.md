# Patent disclosure preparation guide

Use this guide to prepare a private invention disclosure for counsel. Do not
complete the confidential disclosure in this repository.

## Required disclosure sections

1. **Title and family identifier** — use the sanitized public identifier.
2. **Problem** — identify the concrete computer or distributed-system problem.
3. **Existing approaches** — state technical limitations without unsupported
   market or novelty claims.
4. **Technical mechanism** — describe data structures, state transitions,
   validation, control flow, failure handling, and boundaries.
5. **End-to-end embodiment** — provide enough detail to implement a working
   version without relying on the desired result as a black box.
6. **Alternative embodiments** — model-independent, storage-independent,
   centralized/distributed, offline/online, and constrained variants where
   genuinely supported.
7. **Drawings** — architecture, sequence, state-machine, data-lineage, and
   authorization-boundary figures.
8. **Examples and tests** — identify executable examples, expected outputs, and
   failure cases. Keep protected labels and trade-secret values external.
9. **Advantages** — tie each advantage to a concrete technical mechanism and
   measurable computer-system behavior.
10. **Conception history** — human contributors, dates, records, and the specific
    subject matter each person conceived.
11. **Ownership and funding** — assignments, employment/contract status, grant
    obligations, third-party code/data/model terms, and joint-development risk.
12. **Disclosure history** — papers, repositories, talks, demos, offers, sales,
    customer access, emails, and other external access with exact dates.
13. **Patent/trade-secret boundary** — what may be disclosed and what must remain
    confidential.

## Enablement review

Before counsel review, confirm that the disclosure answers:

- What exact inputs are accepted?
- What typed intermediate state is created?
- What algorithm or state machine transforms the inputs?
- What invariants are checked, when, and by which component?
- What happens when information is missing, contested, malformed, stale, or
  unauthorized?
- What is learned and what remains deterministic?
- How are proposals, authorizations, commits, outcomes, and replays linked?
- How does the implementation avoid the identified technical failure?
- Which variants are actually supported by the specification?
- Which source files and test records demonstrate the embodiment?

An aspirational statement such as “the system transfers to unseen
institutions” is not a substitute for describing the training, representation,
runtime, evaluation, and adaptation mechanisms that allegedly produce that
behavior.

## Evidence labels

Every factual result cited in a disclosure should carry one label:

- `IMPLEMENTED_AND_TESTED`
- `IMPLEMENTED_NOT_TESTED`
- `PROTOCOL_ONLY`
- `PROPOSED_VARIANT`
- `NEGATIVE_RESULT`

Do not remove negative results. They may clarify the actual invention boundary
and prevent unsupported drafting.

## Private-storage rule

Completed disclosures, draft claims, counsel comments, filing credentials,
receipts containing private data, assignments, and signatures remain in a
restricted legal workspace. The public registry records only sanitized status
and approved public identifiers.