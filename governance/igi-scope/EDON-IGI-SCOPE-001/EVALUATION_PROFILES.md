# Evaluation profiles

Scope-001 freezes three nested finite profiles. An evaluation must name exactly
one profile and may choose smaller values, never larger values, without creating
a successor scope.

| Bound | EventNet Core | Coordinated Operations | Federated Institution |
| --- | ---: | ---: | ---: |
| Typed state paths | 256 | 512 | 1024 |
| Roles | 32 | 64 | 128 |
| Active agents | 32 | 128 | 256 |
| Resource types | 32 | 128 | 256 |
| Simultaneous goals | 8 | 32 | 64 |
| Plan steps | 128 | 512 | 1024 |
| Queued events | 128 | 512 | 1024 |
| Decision horizon, events | 256 | 2048 | 4096 |
| Mechanism instances | 64 | 128 | 256 |
| Authority/delegation depth | 8 | 16 | 32 |
| Federation scopes | 1 | 8 | 32 |
| Tool calls per episode | 32 | 128 | 256 |
| Maximum observation delay, logical ticks | 64 | 256 | 512 |
| Serialized observation size | 64 KiB | 256 KiB | 1 MiB |

## Compute and adaptation budget

Every evaluation must freeze the model and tokenizer revisions, adapter hashes,
maximum input/output tokens, tool-call budget, wall-clock or accelerator budget,
retrieval budget, demonstrations, and number of adaptation episodes.

Scope-wide caps are:

- 32,768 input tokens per decision;
- 4,096 generated tokens per decision;
- 256 tool calls per episode;
- 100 non-protected adaptation episodes before a protected score;
- zero gradient updates or protected-label access during protected evaluation.

These are admissible maxima, not claims that the current 4B model supports them.

## Transfer-008 coverage

Transfer-008 is restricted to the `EVENTNET_CORE_V1` profile and four task
families: certificate, transition, queue trace, and pair contrast. Even a full
Transfer-008 pass would not test goal formation, planning, allocation, tool use,
long-horizon replanning, federation, real data, or external replication.