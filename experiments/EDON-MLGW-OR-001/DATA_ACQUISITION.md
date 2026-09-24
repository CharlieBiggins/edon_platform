# Data acquisition and readiness

## Public development sources

- NWS event chronology, warnings, wind reports, and weather progression;
- official MLGW outage-map snapshots and restoration updates;
- official city, emergency-management, road, school, and shelter notices;
- public mutual-aid and workforce announcements;
- prior official outage-improvement and after-action material.

Public sources can support outage-curve reconstruction and protocol development.
They cannot recover the internal information state or actual decision process.

## Required partner data

| Dataset | Minimum fields | Purpose |
| --- | --- | --- |
| OMS/CARES events | immutable ID, device abstraction, start/discovery/update/close times, customers interrupted | outage state and information timing |
| SCADA/switching | event time, abstract device, state, operator approval, validator result | energization and safety chronology |
| Work orders | job, damage class, prerequisites, assignment, arrival, start, finish, disposition | actual baseline and service time |
| Crews | pseudonymous crew ID, qualifications, shift, availability, location zone | matched resource pool |
| Vehicles/equipment | capability, availability, assignment | feasibility constraints |
| Materials | item class, depot zone, quantity over time, reservations | inventory constraints |
| Damage assessment | report time, confirmation time, damage class, confidence | information boundary |
| Roads/trees | obstruction, discovery, clearance resources, clearance time | access dependencies |
| Critical services | minimized facility class, dependency, outage interval | protected priority endpoint |
| Weather | time and zone observations/forecasts available operationally | hazard and access state |
| Costs | independently defined labor, mutual aid, materials, logistics | secondary economic endpoint |
| Decision log | alternatives visible, chosen action, timestamp, reason code | actual controller reconstruction |

## Readiness gates

1. Written institutional authorization and named data owner.
2. Independent custodian and role separation.
3. Source/version/time-zone dictionary frozen.
4. At least 99% of event records have valid event and availability timestamps.
5. Crew, job, device, and material identities resolve without collisions.
6. Actual decisions can be reconstructed without using final outcomes.
7. Customer counts reconcile to declared tolerances.
8. Safety and switching records have qualified review.
9. Missingness and correction processes are explicitly modeled.
10. Protected bytes remain outside Git and training releases.

Failure of a readiness gate blocks protected replay rather than triggering
silent imputation.