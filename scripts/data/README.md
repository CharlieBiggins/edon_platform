# Data scripts

Source registration, compiler preparation, qualification, and manifest tooling.

`import_actionnet_world.py` imports and hash-verifies the complete ActionNet
simulation lineage from `ACTIONNET-DATA-QUAL-001` through
`ACTIONNET-DATA-QUAL-008`. It prefers the preserved research archive when it is
available and falls back to the self-contained packages already under
`experiments/` after the repository is downloaded elsewhere.

ActionNet-008 is installed as a runtime-loadable simulation and governed
authoring world. Its records remain `training_eligible=false`; importing the
world does not authorize Cerebrum training.