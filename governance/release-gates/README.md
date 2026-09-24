# Release gates

## Research release

- repository validation passes;
- IP/public-disclosure review passes for the exact material being released;
- claims link to frozen experiment manifests;
- negative results and limitations are included;
- protected artifacts are excluded;
- license and citation metadata are approved.

## IP and publication release

- prior-public-disclosure inventory is complete;
- affected candidate invention families are identified;
- counsel disposition and filing/publication decision are recorded;
- no unapproved trade-secret or protected-evaluation content is included;
- inventorship, ownership, dependency, model, data, and customer rights are
  reviewed;
- trademark language and symbols match the verified register;
- “patent pending” is used only for subject matter mapped to a verified filing;
- IP status is not presented as evidence of scientific performance.

Use `governance/ip/release-review.template.json`. It intentionally defaults to
all checks false and release unauthorized.

## Model release

- model and training-data lineage are complete;
- safety and transfer gates match the advertised claim;
- adapter license and storage controls are approved;
- no protected evaluation data contaminated training.

## Production release

Not currently authorized. It additionally requires source-grounded validation,
security review, institution-specific approvals, rollback, monitoring, incident
response, and deterministic authority controls.