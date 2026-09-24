# Models

Git stores model configurations and manifests only. Adapters and checkpoints live
in an artifact store with immutable hashes, licenses, lineage, and revocation.

C1 is the architectural name for the learned model inside the Cerebrum System.
Historical model manifests and experiments retain the name Cerebrum. New C1
manifests use `schemas/cerebrum/c1-model-manifest.schema.json` and must bind the
base model, optional adapter, training release, evaluation, license, and
revocation status. Operational experience never updates weights automatically.

Routine generations use names such as `C1-v1` and `C1-v2`. A version must bind
an immutable Global ActionNet training release, protected evaluation
reservation, artifact, evaluation, predecessor, license, and release
disposition. The registry records lineage but does not train, load, deploy, or
switch a model automatically.