# Custody, privacy, and infrastructure security

This repository stores schemas, hashes, minimized examples, and public-source
references only. It must not store raw customer data, exact protected topology,
credentials, switching instructions, crew personal data, critical-facility
locations, or internal vulnerability information.

## Roles

- Institution owner: authorizes scope and permitted uses.
- Data custodian: holds protected bytes, labels, seeds, and scoring authority.
- Simulator team: constructs the environment without candidate tuning access.
- Controller teams: receive only frozen development interfaces.
- Safety reviewers: approve constraints and adjudicate violations.
- Statistical reviewer: freezes analysis and executes or witnesses scoring.

No person may both tune a candidate on protected outcomes and authorize the
final score.

## Controls

- tenant-scoped encrypted storage and least privilege;
- pseudonymous crew and job identifiers;
- zone-level rather than unnecessary precise locations;
- immutable access and export logs;
- source-byte, dataset, runtime, prediction, and score hashes;
- protected-set overlap and duplicate checks;
- explicit retention and destruction schedule;
- incident-response and revocation procedures;
- no automatic model-weight update from pilot records;
- no operational execution token in any learned-model context.

Detailed operational artifacts require an institution-approved secure
environment and may not be copied into this public research tree.