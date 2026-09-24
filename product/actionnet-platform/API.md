# API surface

| Endpoint | Required permission | Purpose |
| --- | --- | --- |
| `/api/actionnet-platform/mechanisms` | `actionnet_author` | Register a mechanism version |
| `/api/actionnet-platform/institutional-ir` | `actionnet_author` | Register canonical versioned Institutional IR |
| `/api/actionnet-platform/compositions` | `actionnet_author` | Register an evidence-graded edge |
| `/api/actionnet-platform/compositions/execute` | `actionnet_author` | Instantiate and replay an executable composition |
| `/api/actionnet-platform/counterfactuals/generate` | `actionnet_author` | Generate replay-verified child experiences |
| `/api/actionnet-platform/behavior/scenarios` | `actionnet_author` | Generate bounded assumption-driven actor scenarios |
| `/api/actionnet-platform/intake` | `actionnet_intake` | Accept a locally minimized governed abstraction |
| `/api/actionnet-platform/worlds/generate` | `actionnet_author` | Generate and freeze a world blueprint |
| `/api/actionnet-platform/experiences` | `actionnet_author` | Record a governed experience |
| `/api/actionnet-platform/reviews` | `actionnet_review` | Submit role-bound review |
| `/api/actionnet-platform/overlap-checks` | `actionnet_custody` | Record protected/duplicate checks |
| `/api/actionnet-platform/quarantine` | `actionnet_custody` | Append a quarantine event |
| `/api/actionnet-platform/exposures` | `actionnet_custody` | Record model exposure |
| `/api/actionnet-platform/training-eligibility` | `actionnet_release` | Approve eligible experience |
| `/api/actionnet-platform/releases` | `actionnet_release` | Freeze a training release |
| `/api/actionnet-platform/coverage` | `actionnet_read` | Compute registered coverage |
| `/api/actionnet-platform/coverage/freeze` | `actionnet_curriculum` | Freeze a coverage snapshot |
| `/api/actionnet-platform/acquisition` | `actionnet_curriculum` | Recommend missing experience |
| `/api/actionnet-platform/interventions` | `actionnet_intervention` | Record a non-binding intervention |
| `/api/actionnet-platform/audit` | `actionnet_custody` | Retrieve and verify audit custody |
| `/api/actionnet-platform/institutional-ir/query` | `actionnet_read` | List visible IR versions |
| `/api/actionnet-network/promotions` | `actionnet_global` | Promote one qualified local abstraction into Global ActionNet |
| `/api/actionnet-network/releases` | `actionnet_global` | Freeze an offline global training release |
| `/api/c1/versions` | `c1_release` | Register an immutable frozen C1 version |
| `/api/c1/dispositions` | `c1_release` | Record evidence-gated eligibility, rollback, revocation, or archive disposition |

Authenticated actor and reviewer identities are derived from bearer tokens.
Clients cannot select their own reviewer role, author identity, custodian
identity, or release-manager identity.