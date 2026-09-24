# Protocol

The frozen reference scenario requires ten gates:

1. shadow proposals do not mutate world state;
2. assignment respects agent capabilities;
3. dispatch reserves resources atomically;
4. reported success cannot replace missing expected evidence;
5. failed outcomes require replanning;
6. learning candidates remain ineligible for training;
7. replanning preserves the superseded plan;
8. the world event chain replays exactly;
9. outbox messages can be leased and delivered;
10. Kernel tokens remain bound to the exact request.