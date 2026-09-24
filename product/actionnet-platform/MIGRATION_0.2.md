# Migration from Platform 001 to Platform 002

The SQLite store performs an additive migration when opened:

- the existing Platform 001 tables and records are preserved;
- the metadata version advances to `actionnet-platform-store.v2`;
- new immutable tables are created for Institutional IR, composition runs,
  counterfactual batches, behavior scenarios, and governed intakes;
- existing mechanisms remain valid registry entries, but a mechanism must use
  typed executable transitions before the Composition Engine can execute it;
- existing counterfactual records remain preserved; active generation requires
  a parent trajectory created by the Platform 002 Composition Engine.

Before upgrading a deployment copy:

1. Stop writers.
2. Run `scripts/actionnet/backup_platform.py`.
3. Verify the backup with `scripts/actionnet/verify_backup.py`.
4. Start Platform 002 against a staging copy.
5. Run both Platform 001 and Platform 002 evaluations.
6. Rehearse rollback using the verified backup.

This additive reference migration is not a substitute for a production
database migration, high-availability rehearsal, or external authorization.