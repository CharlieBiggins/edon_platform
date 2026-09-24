# CEREBRUM-DEV-019-DIAGNOSTIC

DEV-019 performs no training and does not modify DEV-018. It evaluates the
unchanged DEV-017 checkpoint-24 model on 32 fresh scenarios under five
cumulative, schema-matched conditions:

1. raw observation;
2. gold typed events;
3. gold event order;
4. gold predecision state; and
5. gold decision.

All five conditions for a scenario share the same expected certificate. Paired
recovery identifies the earliest intervention under which a previously failed
scenario becomes correct. This localizes an earliest demonstrated failure
stage; it does not prove a unique cause.