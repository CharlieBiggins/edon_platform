# Formal scope

## 1. Environment class

An admissible institutional environment is a finite constrained partially
observable stochastic game

\[
M=(S,O,A,T,Z,G,K,H),
\]

where (S) is typed institutional state, (O) is the observation space, (A)
is the non-binding proposal space, (T) is the event-driven transition kernel,
(Z) is the information-release process, (G) is the registered objective
set, (K) is the authority/policy/safety/resource constraint system, and (H)
is a finite event horizon.

Cerebrum controls proposals in (A). It does not control binding state
transitions. Every binding transition remains outside the learned policy and
requires deterministic Kernel authorization.

The Scope-001 universe is

\[
\mathcal U_{001}=\{M:\ M\text{ satisfies the registered grammar, profiles, and
safety assumptions in }\texttt{scope.json}\}.
\]

The universe is a generative class, not an enumeration of institutions.

## 2. Institutional grammar

Every environment must be expressible as a typed composition of registered
authority, delegation, jurisdiction, approval, revocation, appeal, evidence,
policy, temporal, workflow, resource, conflict, dependency, queue, and
federation mechanisms. Missing, conflicting, expired, contested, and malformed
conditions remain explicit semantic states rather than being silently repaired.

## 3. Observability

Scope-001 permits partial, delayed, missing, noisy, contradictory, and
out-of-order observations. Information is time-gated: an agent may use only
facts released by the current decision time. Permanent uncertainty is allowed,
but a safe abstention must remain available.

## 4. Generality claim tuple

Every evaluation claim must instantiate

\[
C=(\mathcal U,\mathcal D,\mathcal T,\mathcal B,\Phi),
\]

where \(\mathcal D\) is the institution distribution, \(\mathcal T\) is the task
set, \(\mathcal B\) is the model/adaptation/compute budget, and \(\Phi\) is the
safety invariant set. Results without all five components cannot be promoted
into a Scope-001 generality claim.

An empirical claim has the form

\[
\Pr_{M\sim\mathcal D_{test}}[
V^{\pi}_{safe}(M)\ge V^{b}_{safe}(M)+\Delta
\land \operatorname{violations}_{\pi}(M)=0]
\ge 1-\delta,
\]

under matched information, tools, time, and compute. A universal theorem would
instead require a statement quantified over every (M\in\mathcal U_{001}).
Scope-001 currently authorizes neither statement as an established result.

## 5. Transfer and adaptation

Protected evaluation institutions must be disjoint from training by institution
identity, case and pair identity, prompt hash, renderer, reserved semantic
family, and protected generator lineage. Strong independent-transfer evidence
also requires an independently implemented generator/oracle or independently
authored real institution.

Within a protected episode, adaptation may use observations, governed memory,
and registered tools. Gradient updates, label access, evaluator feedback, and
case-specific prompt repair are prohibited.

## 6. What “general” means here

“General” means successful adaptation across the registered variation axes
within Scope-001, not competence over arbitrary computation, every human
institution, unrestricted physical control, or every future environment.

Representation coverage, learned adaptation, performance, and safety are four
separate obligations. Evidence for one does not imply the others.