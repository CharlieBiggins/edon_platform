# Preservation note

The complete archived `ACTIONNET-DATA-QUAL-005` implementation is present in
this package and regenerates its 5,040 training records, 420 fresh validation
records, 600 trajectories, lineage records, checksum inventory, and 31/31
qualification controls.

The archive's frozen `results/result_manifest.json` references earlier source,
documentation, and test hashes that do not match the source bytes retained in
the archive. Those earlier bytes are not available in this workspace. The
archived manifest is therefore retained without alteration as
`results/preserved_result_manifest.json`; a campaign run writes the active
`results/result_manifest.json` from the source bytes that are actually present.

The dataset and qualification artifact hashes reproduce. The discrepancy is
limited to the result manifest's source/document inventory and is recorded
rather than silently repaired. No claim of exact DATA-QUAL-005 source-byte
restoration is made.