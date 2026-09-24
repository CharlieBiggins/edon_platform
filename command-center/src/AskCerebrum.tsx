import { useEffect, useMemo, useRef, useState } from 'react';
import { Activity, ArrowLeft, ArrowRight, Bookmark, Boxes, CheckCircle2, ChevronRight, Clock3, Columns2, Expand, FileCheck2, Focus, GitBranch, Link2, ListChecks, LockKeyhole, Maximize2, Minimize2, Minus, Network, Plus, RotateCcw, Search, Send, ShieldCheck, Sparkles, TrendingUp, Users, X } from 'lucide-react';
import { Badge } from './components';
import { evidenceFor, money } from './data';
import type { Activity as ActivityRecord, Incident, Page, Plan, Receipt, Scenario } from './types';

type AskMode = 'docked' | 'expanded' | 'full';
type WorkspaceDensity = 'comfortable' | 'compact';
type AnalysisKind = 'explanation' | 'summary' | 'plans' | 'evidence' | 'timeline' | 'commitments' | 'proposal' | 'graph' | 'outcome';
type Message = { id: number; role: 'user' | 'cerebrum'; text: string; kind?: AnalysisKind };
type InspectorTab = 'evidence' | 'timeline' | 'commitments' | 'plans' | 'graph' | 'decision' | 'outcome' | 'receipts';

interface AskCerebrumProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  incident: Incident;
  plan: Plan;
  page: Page;
  version: number;
  scenario: Scenario;
  activities: ActivityRecord[];
  receipt?: Receipt;
  onShowEvidence: () => void;
  onComparePlans: () => void;
  onReviewProposal: () => void;
  onOpenReceipt: () => void;
  onOpenReconstruction: () => void;
  onNotify: (message: string) => void;
  scope: { label: string; detail: string };
}

const prompts = [
  'Summarize this incident',
  'What changed in the last hour?',
  'Which commitments are affected?',
  'What evidence is missing?',
  'Why is human approval required?',
];
const pageLabels: Record<Page, string> = { overview: 'Operations Overview', queue: 'Work Queue', incident: 'Cerebrum Workspace', reviews: 'Human reviews', outcomes: 'Shadow & outcomes', receipts: 'Receipt Inspector', value: 'Value report', state: 'Institutional state', integrations: 'Integration health', settings: 'Settings & Administration', location: 'Location Overview', actor: 'Actor Inspector', reconstructions: 'Reconstructions', exceptions: 'Execution exceptions', integrity: 'Integrity status', holds: 'Legal holds', exports: 'Audit exports', builder: 'Institution Builder' };

function classify(question: string): AnalysisKind {
  const value = question.toLowerCase();
  if (/(move|reroute|reserve|spend|authorize|execute)/.test(value)) return 'proposal';
  if (/(afterward|outcome|result|happened after|observed effect)/.test(value)) return 'outcome';
  if (/(dependency|dependencies|control graph|relationship|chain)/.test(value)) return 'graph';
  if (/(compare|alternative|simulation|what-if|what if|plan)/.test(value)) return 'plans';
  if (/(evidence|missing|conflict|source)/.test(value)) return 'evidence';
  if (/(changed|timeline|last hour|history)/.test(value)) return 'timeline';
  if (/(commitment|customer|affected)/.test(value)) return 'commitments';
  if (/(approval|kernel|authority|mandate)/.test(value)) return 'explanation';
  return 'summary';
}

function answer(kind: AnalysisKind, incident: Incident, plan: Plan) {
  if (kind === 'proposal') return 'I can prepare that proposal, but I cannot authorize it. I have converted the request into a simulated structured draft for formal review.';
  if (kind === 'graph') return `The dependency chain begins with the Memphis capacity constraint, affects ${incident.orders} orders, threatens ${incident.commitments} commitments, and depends on Nashville capacity plus missing carrier evidence.`;
  if (kind === 'outcome') return 'The operator extended local overtime. The simulated record shows a 10.2-hour recovery and $15,800 recorded cost; independent outcome adjudication is still pending.';
  if (kind === 'plans') return `Three modeled recovery plans are available. ${plan.name} currently balances protected commitments, recovery time, and operational risk.`;
  if (kind === 'evidence') return 'Six accessible evidence records inform this assessment. Carrier capacity remains missing, one operating condition is an assumption, and one attachment is restricted.';
  if (kind === 'timeline') return 'The disruption was observed at 10:24 CDT. Capacity evidence arrived at 10:31, and the shadow recommendation was recorded at 10:42. No action was authorized or executed.';
  if (kind === 'commitments') return `${incident.commitments} delivery commitments and ${incident.orders} orders are in scope. The earliest modeled breach condition occurs before the 16:00 CDT carrier cutoff.`;
  if (kind === 'explanation') return `The recommended plan has a modeled cost of ${money(plan.cost)} and requests Nashville capacity. The assigned agent mandate permits only $10,000 without human review.`;
  return `${incident.title} reduced available outbound capacity. ${incident.commitments} commitments are at risk, with ${incident.timeRemaining} remaining in the simulated decision window.`;
}

function PlanObject({ incident, selected, onCompare }: { incident: Incident; selected: Plan; onCompare: () => void }) {
  return <div className="ask-object ask-plan-object"><div className="ask-object-head"><span><Columns2 size={15} /> Plan comparison</span><Badge tone="blue">Modeled</Badge></div><div className="ask-plan-rows">{incident.plans.map(plan => <div key={plan.id} className={plan.id === selected.id ? 'selected' : ''}><span><strong>{plan.name}</strong><small>{plan.kind}</small></span><span><b>{plan.protected}/{incident.commitments}</b><small>protected</small></span><span><b>{money(plan.cost)}</b><small>estimated</small></span><span><b>{plan.recovery}</b><small>recovery</small></span></div>)}</div><button onClick={onCompare}>Open formal comparison <ArrowRight size={13} /></button></div>;
}

function EvidenceObject({ incident, onShowEvidence }: { incident: Incident; onShowEvidence: () => void }) {
  const evidence = evidenceFor(incident);
  return <div className="ask-object"><div className="ask-object-head"><span><Search size={15} /> Evidence status</span><Badge tone="amber">2 unresolved</Badge></div><div className="ask-evidence-list">{evidence.slice(0, 4).map(item => <div key={item.id}><span className={`ask-evidence-dot ${item.status.toLowerCase()}`} /><span><strong>{item.title}</strong><small>{item.id} · {item.status}</small></span></div>)}</div><button onClick={onShowEvidence}>Inspect all accessible evidence <ArrowRight size={13} /></button></div>;
}

function TimelineObject({ activities }: { activities: ActivityRecord[] }) {
  return <div className="ask-object"><div className="ask-object-head"><span><Clock3 size={15} /> Institutional timeline</span><Badge>Simulated</Badge></div><ol className="ask-mini-timeline">{activities.slice(0, 3).map(item => <li key={item.id}><i className={item.tone} /><span><small>{item.time}</small><strong>{item.title}</strong></span></li>)}</ol></div>;
}

function CommitmentObject({ incident }: { incident: Incident }) {
  return <div className="ask-object"><div className="ask-object-head"><span><GitBranch size={15} /> Commitment path</span><Badge tone="amber">At risk</Badge></div><div className="commitment-path" tabIndex={0} aria-label={`Sortation outage affects ${incident.orders} orders, threatens ${incident.commitments} commitments, before the 16:00 cutoff`}><span>Sortation outage</span><ChevronRight size={13} /><span>{incident.orders} orders</span><ChevronRight size={13} /><span>{incident.commitments} commitments</span><ChevronRight size={13} /><span>16:00 cutoff</span></div></div>;
}

function ProposalObject({ incident, onReview }: { incident: Incident; onReview: () => void }) {
  return <div className="ask-object ask-proposal-object"><div className="ask-object-head"><span><FileCheck2 size={15} /> Structured action proposal</span><Badge tone="amber">DRAFT · SIMULATED</Badge></div><div className="ask-proposal-scope"><span><CheckCircle2 size={14} /> Reserve Nashville capacity</span><span><CheckCircle2 size={14} /> Reroute {incident.orders.toLocaleString()} in-scope orders</span><span><CheckCircle2 size={14} /> Set a modeled ceiling of $50,000</span><span><CheckCircle2 size={14} /> Affect {incident.commitments} customer commitments</span></div><div className="ask-authority-boundary"><LockKeyhole size={15} /><span><strong>No authority granted</strong>This draft cannot reserve resources, approve itself, or execute.</span></div><button onClick={onReview}>Review structured proposal <ArrowRight size={13} /></button></div>;
}

function AnalysisObject({ message, props }: { message: Message; props: AskCerebrumProps }) {
  if (message.kind === 'plans') return <PlanObject incident={props.incident} selected={props.plan} onCompare={props.onComparePlans} />;
  if (message.kind === 'evidence') return <EvidenceObject incident={props.incident} onShowEvidence={props.onShowEvidence} />;
  if (message.kind === 'timeline') return <TimelineObject activities={props.activities} />;
  if (message.kind === 'commitments') return <CommitmentObject incident={props.incident} />;
  if (message.kind === 'proposal') return <ProposalObject incident={props.incident} onReview={props.onReviewProposal} />;
  if (message.kind === 'graph') return <CommitmentObject incident={props.incident} />;
  if (message.kind === 'outcome') return <div className="ask-incident-card"><span><strong>SIMULATED OUTCOME</strong><Badge tone="amber">Pending verification</Badge></span><h4>{props.incident.operatorAction}</h4><div><span><small>Observed recovery</small><b>{props.incident.actualRecovery}</b></span><span><small>Recorded cost</small><b>{money(props.incident.actualCost)}</b></span></div></div>;
  if (message.kind === 'explanation') return <div className="ask-fact-grid"><span><small>Evidence</small><strong>6 accessible records</strong></span><span><small>Assumptions</small><strong>2 unresolved</strong></span><span><small>Policy certainty</small><strong><ShieldCheck size={13} /> Verified fixture</strong></span></div>;
  return <div className="ask-incident-card"><span><strong>{props.incident.id}</strong><Badge tone="red">{props.incident.severity}</Badge></span><h4>{props.incident.title}</h4><div><span><small>Modeled exposure</small><b>${Math.round(props.incident.exposure / 1000)}K</b></span><span><small>Decision window</small><b>{props.incident.timeRemaining}</b></span></div></div>;
}

type GraphNodeId = 'memphis' | 'orders' | 'commitments' | 'nashville' | 'carrier';
const graphDetails: Record<GraphNodeId, { title: string; kind: string; owner: string; freshness: string; authority: string; evidence: string; connections: string }> = {
  memphis: { title: 'Memphis capacity', kind: 'Operational resource', owner: 'Memphis site operations', freshness: 'Observed 2 minutes ago', authority: 'Site operations may report; Kernel governs consequential proposals', evidence: 'EV-2081 · Observed', connections: '640 orders · Nashville capacity' },
  orders: { title: '640 affected orders', kind: 'Workflow population', owner: 'Customer operations', freshness: 'State v142 · current fixture', authority: 'Read-only projection', evidence: 'EV-2082 · Verified fixture', connections: 'Memphis capacity · 4 commitments' },
  commitments: { title: '4 threatened commitments', kind: 'Institutional obligations', owner: 'Customer operations', freshness: 'Ledger v8 · 10:27 CDT', authority: 'Renegotiation requires commitment-owner review', evidence: 'EV-2082 · 1 restricted attachment omitted', connections: '640 orders · 4 customer beneficiaries' },
  nashville: { title: 'Nashville capacity', kind: 'Proposed recovery resource', owner: 'Regional operations', freshness: 'Reported at 10:31 CDT', authority: 'Reservation requires formal proposal and Kernel decision', evidence: 'EV-2083 · Reported', connections: '4 commitments · carrier capacity' },
  carrier: { title: 'Carrier evidence', kind: 'Required dependency', owner: 'Transport desk', freshness: 'Missing at 10:42 CDT', authority: 'Cannot be inferred or waived conversationally', evidence: 'EV-2085 · Missing', connections: 'Nashville capacity · 16:00 cutoff' },
};

function GraphExplorer({ incident, onNotify }: { incident: Incident; onNotify: (message: string) => void }) {
  const [selected, setSelected] = useState<GraphNodeId>('commitments');
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState(0);
  const [expanded, setExpanded] = useState(true);
  const [snapshot, setSnapshot] = useState(3);
  const nodes: { id: GraphNodeId; title: string; detail: string; tone: string; restricted?: boolean }[] = [
    { id: 'memphis', title: 'Memphis capacity', detail: '38% constrained', tone: 'critical' },
    { id: 'orders', title: `${incident.orders} orders`, detail: 'affected', tone: 'warning' },
    { id: 'commitments', title: `${incident.commitments} commitments`, detail: 'threatened', tone: 'critical', restricted: true },
    { id: 'nashville', title: 'Nashville capacity', detail: 'required', tone: 'selected' },
    { id: 'carrier', title: 'Carrier evidence', detail: 'missing', tone: 'missing' },
  ];
  const visible = expanded ? nodes : nodes.slice(0, 3);
  const relationships = ['affects', 'threatens', 'requires', 'depends on'];
  const times = ['10:18 · occurred', '10:24 · observed', '10:31 · capacity reported', '10:42 · recommendation'];
  const details = graphDetails[selected];
  return <div className="control-graph"><div className="graph-toolbar"><div><button aria-label="Zoom out" onClick={() => setZoom(value => Math.max(.75, value - .1))}><Minus size={14}/></button><span>{Math.round(zoom * 100)}%</span><button aria-label="Zoom in" onClick={() => setZoom(value => Math.min(1.35, value + .1))}><Plus size={14}/></button></div><div><button aria-label="Pan left" onClick={() => setPan(value => Math.min(80, value + 30))}><ArrowLeft size={14}/></button><button aria-label="Pan right" onClick={() => setPan(value => Math.max(-80, value - 30))}><ArrowRight size={14}/></button><button aria-label="Reset graph view" onClick={() => { setZoom(1); setPan(0); }}><RotateCcw size={14}/></button></div><button className="graph-expand" onClick={() => setExpanded(value => !value)}>{expanded ? 'Collapse dependencies' : 'Expand dependencies'}</button></div><div className="graph-viewport"><div className="graph-chain" style={{ transform: `translateX(${pan}px) scale(${zoom})` }}>{visible.map((node, index) => <div className="graph-step" key={node.id}>{index > 0 && <button className="graph-edge" title={`${visible[index - 1].title} ${relationships[index - 1]} ${node.title}`} onClick={() => onNotify(`${visible[index - 1].title} ${relationships[index - 1]} ${node.title}. Relationship explanation is simulated.`)}><span>{relationships[index - 1]}</span><ArrowRight size={19}/></button>}<button className={`graph-node-button ${node.tone} ${selected === node.id ? 'active' : ''}`} onClick={() => setSelected(node.id)} aria-pressed={selected === node.id}><span>{node.title}</span><small>{node.detail}</small>{node.restricted && <i title="Restricted dependency omitted"><LockKeyhole size={11}/> 1 restricted</i>}</button></div>)}</div></div><div className="graph-time"><div><Clock3 size={13}/><span>State timeline</span><strong>{times[snapshot]}</strong></div><input aria-label="Control Graph timeline" type="range" min="0" max="3" step="1" value={snapshot} onChange={event => setSnapshot(Number(event.target.value))}/><div><span>10:18</span><span>10:24</span><span>10:31</span><span>10:42</span></div></div><aside className="graph-node-inspector"><div><span className="eyebrow">SELECTED NODE</span><h4>{details.title}</h4><Badge tone={selected === 'carrier' ? 'amber' : selected === 'memphis' || selected === 'commitments' ? 'red' : 'blue'}>{details.kind}</Badge></div><dl><div><dt>Evidence</dt><dd>{details.evidence}</dd></div><div><dt>Owner</dt><dd>{details.owner}</dd></div><div><dt>Freshness</dt><dd>{details.freshness}</dd></div><div><dt>Authority</dt><dd>{details.authority}</dd></div><div><dt>Connected commitments</dt><dd>{details.connections}</dd></div></dl><button onClick={() => onNotify(`Relationship explanation prepared for ${details.title}. No institutional state was changed.`)}><Link2 size={13}/> Explain this relationship</button></aside></div>;
}

function Inspector({ tab, setTab, props }: { tab: InspectorTab; setTab: (tab: InspectorTab) => void; props: AskCerebrumProps }) {
  const evidence = evidenceFor(props.incident);
  const [simulationRun, setSimulationRun] = useState(false);
  const tabs: [InspectorTab, string, typeof Search][] = [['evidence', 'Evidence', Search], ['timeline', 'Timeline', Activity], ['commitments', 'Commitments', ListChecks], ['plans', 'Plans', Columns2], ['graph', 'Control Graph', Network], ['decision', 'Decision', ShieldCheck], ['outcome', 'Outcome', TrendingUp], ['receipts', 'Receipts', FileCheck2]];
  return <section className="ask-inspector" aria-label="Investigation objects"><div className="ask-inspector-tabs" role="tablist">{tabs.map(([id, label, Icon]) => <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)}><Icon size={14} />{label}</button>)}</div><div className="ask-inspector-body" role="tabpanel">
    {tab === 'evidence' && <><div className="ask-inspector-title"><div><span className="eyebrow">ACCESSIBLE EVIDENCE</span><h3>Evidence inspector</h3></div><Badge tone="amber">2 unresolved</Badge></div>{evidence.map(item => <button className="ask-evidence-row" key={item.id} onClick={props.onShowEvidence}><span className={`ask-evidence-dot ${item.status.toLowerCase()}`} /><span><strong>{item.title}</strong><small>{item.source} · {item.id} · {item.version}</small></span><Badge tone={item.status === 'Verified' ? 'teal' : item.status === 'Restricted' ? 'neutral' : 'amber'}>{item.status}</Badge></button>)}</>}
    {tab === 'timeline' && <><div className="ask-inspector-title"><div><span className="eyebrow">POINT-IN-TIME STATE</span><h3>Institutional timeline</h3></div><Badge>State v{props.version}</Badge></div><TimelineObject activities={props.activities} /><div className="ask-time-band"><span>10:18</span><i /><span>10:24</span><i /><span>10:31</span><i /><span>10:42</span></div></>}
    {tab === 'commitments' && <><div className="ask-inspector-title"><div><span className="eyebrow">INSTITUTIONAL OBLIGATIONS</span><h3>Affected commitments</h3></div><Badge tone="amber">{props.incident.commitments} at risk</Badge></div><div className="workspace-commitments">{['Priority retail delivery · 14:30', 'Clinical supplies transfer · 15:00', 'Regional replenishment · 15:30', 'Customer cutoff commitment · 16:00'].slice(0, props.incident.commitments).map((item, index) => <article key={item}><span>CMT-{781 + index}</span><strong>{item}</strong><small>{index < 2 ? 'Predicted breach without intervention' : 'Protected by recommended plan'}</small><div><Badge tone={index < 2 ? 'red' : 'amber'}>{index < 2 ? 'Critical' : 'Threatened'}</Badge><span>Owner: Customer operations</span></div></article>)}</div><CommitmentObject incident={props.incident}/></>}
    {tab === 'plans' && <><div className="ask-inspector-title"><div><span className="eyebrow">ALTERNATIVES</span><h3>Recovery-plan comparison</h3></div><Badge tone="blue">Read-only</Badge></div><PlanObject incident={props.incident} selected={props.plan} onCompare={props.onComparePlans} /><div className="ask-simulation"><div><span className="eyebrow">READ-ONLY WHAT-IF</span><strong>Nashville capacity falls to 260 units</strong><small>No institutional state will be changed.</small></div><button onClick={() => setSimulationRun(true)} disabled={simulationRun}>{simulationRun ? 'Simulation complete' : 'Run simulation'}</button>{simulationRun && <p><b>Modeled result:</b> Regional rebalance becomes infeasible at its current scope. Local recovery protects 2 of 4 commitments; a narrowed transfer requires fresh evidence and review.</p>}</div><div className="ask-assumption-register"><strong>Assumption & uncertainty register</strong><span>Carrier capacity confirmation <Badge tone="amber">Missing</Badge></span><span>Capacity through cutoff <Badge tone="amber">Assumption</Badge></span><span>Forecast confidence <Badge tone="blue">Moderate</Badge></span></div></>}
    {tab === 'graph' && <><div className="ask-inspector-title"><div><span className="eyebrow">CONTROL GRAPH SUBSET</span><h3>Dependency explorer</h3></div><Badge>Read-only · simulated</Badge></div><GraphExplorer incident={props.incident} onNotify={props.onNotify}/><p className="ask-inspector-note">This is a permitted projection. Restricted relationships are labeled and omitted rather than inferred.</p></>}
    {tab === 'decision' && <><div className="ask-inspector-title"><div><span className="eyebrow">GOVERNED DECISION</span><h3>Recommendation review</h3></div><Badge tone="amber">Human review required</Badge></div><div className="workspace-decision"><div><span className="eyebrow">CURRENT RECOMMENDATION</span><h4>{props.plan.name}</h4><p>{props.plan.summary}</p></div><dl><div><dt>Modeled cost</dt><dd>{money(props.plan.cost)}</dd></div><div><dt>Resources</dt><dd>{props.plan.resources}</dd></div><div><dt>Commitments protected</dt><dd>{props.plan.protected} of {props.incident.commitments}</dd></div><div><dt>Mandate</dt><dd>MND-MEM-014 · $30,000 ceiling</dd></div><div><dt>Policy</dt><dd>POL-LOG-07 · v18</dd></div><div><dt>Kernel disposition</dt><dd>REVIEW REQUIRED · simulated</dd></div></dl><div className="ask-authority-boundary"><LockKeyhole size={15}/><span><strong>Decision boundary</strong>Conversation can explain or draft. Only the formal review surface can collect a human input for independent Kernel reevaluation.</span></div><button className="workspace-review-button" onClick={props.onReviewProposal}>Review recommendation in formal Decision view <ArrowRight size={14}/></button></div></>}
    {tab === 'outcome' && <><div className="ask-inspector-title"><div><span className="eyebrow">OBSERVED EFFECT</span><h3>Outcome comparison</h3></div><Badge tone="amber">Verification pending</Badge></div><div className="workspace-outcome"><article><span>EXPECTED · {props.plan.name}</span><strong>{props.plan.recovery}</strong><small>{money(props.plan.cost)} modeled cost · {props.plan.protected}/{props.incident.commitments} commitments protected</small></article><ArrowRight size={21}/><article><span>OBSERVED · OPERATOR ACTION</span><strong>{props.incident.actualRecovery}</strong><small>{money(props.incident.actualCost)} recorded cost · mock event log</small></article></div><div className="workspace-outcome-status"><ShieldCheck size={17}/><div><strong>Not a verified Cerebrum outcome</strong><span>Independent evidence reconciliation remains pending. Prediction and observation are kept separate.</span></div></div></>}
    {tab === 'receipts' && <><div className="ask-inspector-title"><div><span className="eyebrow">DECISION HISTORY</span><h3>Receipt record</h3></div><Badge tone="teal">CURRENT</Badge></div><div className="ask-receipt-card"><FileCheck2 size={25}/><span><strong>{props.receipt?.id ?? 'No current receipt'}</strong><small>{props.receipt?.type ?? 'A receipt will be created after a material decision.'}</small></span></div><button className="ask-inspector-action" onClick={props.onOpenReceipt} disabled={!props.receipt}>Open Receipt Inspector <ArrowRight size={14}/></button><button className="ask-inspector-action" onClick={props.onOpenReconstruction}>Open reconstruction <ArrowRight size={14}/></button></>}
  </div></section>;
}

export default function AskCerebrum(props: AskCerebrumProps) {
  const [mode, setMode] = useState<AskMode>('docked');
  const [density, setDensity] = useState<WorkspaceDensity>('comfortable');
  const [input, setInput] = useState('');
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>('evidence');
  const [messages, setMessages] = useState<Message[]>([{ id: 1, role: 'cerebrum', text: 'I am scoped to the current Command Center view. Ask for an explanation, evidence trace, comparison, or read-only simulation.', kind: 'summary' }]);
  const [pinned, setPinned] = useState<number[]>([]);
  const messageId = useRef(2);
  const endRef = useRef<HTMLDivElement>(null);
  const evidence = useMemo(() => evidenceFor(props.incident), [props.incident]);

  useEffect(() => { if (props.open) endRef.current?.scrollIntoView({ block: 'nearest' }); }, [props.open, messages, mode]);
  useEffect(() => {
    function keydown(event: KeyboardEvent) { if (event.key === 'Escape' && props.open) mode === 'full' ? setMode('expanded') : props.onOpenChange(false); }
    window.addEventListener('keydown', keydown); return () => window.removeEventListener('keydown', keydown);
  }, [props.open, mode, props.onOpenChange]);

  function submit(question = input) {
    const clean = question.trim(); if (!clean) return;
    const kind = classify(clean);
    setMessages(prev => [...prev, { id: messageId.current++, role: 'user', text: clean }, { id: messageId.current++, role: 'cerebrum', text: answer(kind, props.incident, props.plan), kind }]);
    setInput('');
    if (kind === 'plans') { setMode('expanded'); setInspectorTab('plans'); }
    if (kind === 'evidence') setInspectorTab('evidence');
    if (kind === 'timeline') setInspectorTab('timeline');
    if (kind === 'commitments') setInspectorTab('commitments');
    if (kind === 'explanation' || kind === 'proposal') setInspectorTab('decision');
    if (kind === 'graph') setInspectorTab('graph');
    if (kind === 'outcome') setInspectorTab('outcome');
  }

  function pinLatest() {
    const latest = [...messages].reverse().find(message => message.role === 'cerebrum');
    if (!latest) return;
    setPinned(current => current.includes(latest.id) ? current.filter(id => id !== latest.id) : [...current, latest.id]);
    props.onNotify(pinned.includes(latest.id) ? 'Answer removed from the simulated workspace pins.' : 'Answer pinned to this simulated investigation.');
  }

  function changeMode(next: AskMode) { setMode(next); props.onOpenChange(true); }

  if (!props.open) return <button className="ask-launcher" onClick={() => props.onOpenChange(true)}><Sparkles size={17}/><span>Ask Cerebrum</span><small>Context-aware · simulated</small></button>;

  const workspaceLabel = mode === 'docked' ? 'Ask Cerebrum docked workspace' : mode === 'expanded' ? 'Cerebrum Workspace expanded' : 'Cerebrum Workspace full investigation';
  return <div className={`ask-layer ask-${mode}`} data-mode={mode}><button className="ask-scrim" aria-label="Close Ask Cerebrum" onClick={() => props.onOpenChange(false)} /><section className={`ask-shell density-${density}`} role="dialog" aria-modal="false" aria-label={workspaceLabel}>
    <header className="ask-header"><div className="ask-brand"><span>{mode === 'docked' ? <Sparkles size={17}/> : <Boxes size={18}/>}</span><div><strong>{mode === 'docked' ? 'CEREBRUM' : 'CEREBRUM WORKSPACE'}</strong><small>{mode === 'docked' ? `Contextual analysis · Incident ${props.incident.id}` : `${props.incident.id} · ${props.incident.title}`}</small></div></div><div className="ask-mode-actions"><button className="density-toggle" aria-label={`Density: ${density === 'comfortable' ? 'Comfortable' : 'Compact'}`} aria-pressed={density === 'compact'} onClick={() => setDensity(value => value === 'comfortable' ? 'compact' : 'comfortable')}>{density === 'comfortable' ? 'Comfortable' : 'Compact'}</button>{mode === 'docked' && <button aria-label="Expand workspace" onClick={() => changeMode('expanded')} title="Expand workspace"><Expand size={15}/><span>Expand workspace</span></button>}{mode === 'expanded' && <><button onClick={() => changeMode('docked')} title="Dock panel"><Minimize2 size={15}/><span>Dock Ask Cerebrum</span></button><button onClick={() => changeMode('full')} title="Full investigation"><Maximize2 size={15}/><span>Full investigation</span></button></>}{mode === 'full' && <button onClick={() => changeMode('expanded')} title="Exit full screen"><Columns2 size={15}/><span>Exit full screen</span></button>}<button aria-label="Close Ask Cerebrum" onClick={() => props.onOpenChange(false)}><X size={17}/></button></div></header>
    <div className="workspace-boundary"><strong>SIMULATED ENVIRONMENT</strong><b>SHADOW MODE</b><span>READ ONLY</span><span><LockKeyhole size={12}/> No authorization or execution available</span></div>
    <div className="workspace-incident-header"><div><span className="eyebrow">{mode === 'full' ? 'FOCUSED INVESTIGATION' : pageLabels[props.page]}</span><h2>{props.incident.title}</h2><p>{props.scope.label} · {props.scope.detail} · {props.incident.id}</p></div><div className="incident-header-status"><span><Activity size={14}/> {props.scenario === 'normal' ? 'Network stable outside incident scope' : `Network state: ${props.scenario}`}</span><span><Clock3 size={14}/> Updated {props.incident.stateFreshness}</span><Badge tone={props.scenario === 'normal' ? 'teal' : 'amber'}>{props.scenario === 'normal' ? 'Current' : props.scenario}</Badge></div>{mode === 'full' && <div className="incident-header-actions"><span><Users size={14}/> Jordan Ellis · Maya Chen</span><button onClick={() => props.onNotify('Investigation assigned to Maya Chen in this simulated session.')}>Assign</button><button onClick={() => props.onNotify('Simulated invitation copied. No message was sent.')}>Share</button></div>}</div>
    <div className="ask-workspace"><section className="ask-conversation" aria-label="Ask Cerebrum conversation">{mode !== 'docked' && <div className="ask-conversation-header"><div><span className="eyebrow">CEREBRUM</span><strong>Contextual analysis · Incident {props.incident.id}</strong></div><div><button onClick={() => changeMode('full')} disabled={mode === 'full'}><Focus size={12}/> {mode === 'full' ? 'Investigation active' : 'Start focused investigation'}</button><button onClick={pinLatest}><Bookmark size={12}/> Pin answer</button><button onClick={() => setInspectorTab('evidence')}><Search size={12}/> Cite evidence</button><button onClick={() => setInspectorTab('plans')}><Columns2 size={12}/> Compare plans</button><button onClick={() => submit('Reserve Nashville capacity and draft a structured proposal for the recommended recovery plan')}><FileCheck2 size={12}/> Draft proposal</button><button onClick={() => props.onNotify('Simulated executive briefing prepared from the current investigation scope.')}><Sparkles size={12}/> Generate briefing</button></div></div>}<div className="ask-messages" role="region" tabIndex={0} aria-label="Ask Cerebrum conversation history">{messages.map(message => <article key={message.id} className={`ask-message ${message.role} ${pinned.includes(message.id) ? 'pinned' : ''}`}><span>{message.role === 'user' ? 'YOU ASKED' : 'CEREBRUM'}{message.role === 'cerebrum' && pinned.includes(message.id) && <b><Bookmark size={10}/> PINNED</b>}</span><p>{message.text}{message.role === 'cerebrum' && <span className="claim-citations"> <button onClick={() => setInspectorTab('evidence')}>[1]</button> <button onClick={() => setInspectorTab('evidence')}>[2]</button> <button onClick={() => setInspectorTab('evidence')}>[3]</button> <button onClick={() => setInspectorTab('evidence')}>[4]</button></span>}</p>{message.role === 'cerebrum' && message.kind && <><AnalysisObject message={message} props={props} /><div className="answer-provenance"><strong>BASED ON</strong><span>6 evidence records</span><span>State v{props.version}</span><span>Policy v18</span><span>2 unresolved assumptions</span><button aria-label={pinned.includes(message.id) ? 'Unpin answer' : 'Pin answer'} onClick={() => setPinned(current => current.includes(message.id) ? current.filter(id => id !== message.id) : [...current, message.id])}><Bookmark size={11}/>{pinned.includes(message.id) ? 'Unpin' : 'Pin'}</button></div></>}</article>)}<div ref={endRef}/></div>
      <div className="ask-composer-region">
        <div className="ask-prompt-list" aria-label="Suggested questions">{prompts.slice(0, mode === 'docked' ? 3 : 5).map(prompt => <button key={prompt} onClick={() => submit(prompt)}>{prompt}</button>)}</div>
        <form className="ask-composer" onSubmit={event => { event.preventDefault(); submit(); }}><label htmlFor="ask-input" className="sr-only">Ask about current institutional context</label><textarea id="ask-input" rows={2} value={input} onChange={event => setInput(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit(); } }} placeholder="Ask about this incident, compare plans, or draft a proposal..."/><button type="submit" aria-label="Send question" disabled={!input.trim()}><Send size={16}/></button><small><LockKeyhole size={11}/> Analysis only. Conversation cannot authorize or execute.</small></form>
      </div>
    </section>{mode !== 'docked' && <Inspector tab={inspectorTab} setTab={setInspectorTab} props={props}/>}</div>
    {mode !== 'docked' && <aside className="decision-rail" aria-label="Persistent decision status"><div><span>DECISION WINDOW</span><strong>{props.incident.timeRemaining.toUpperCase()}</strong></div><dl><div><dt>Modeled exposure</dt><dd>${Math.round(props.incident.exposure / 1000)}K</dd></div><div><dt>Commitments at risk</dt><dd>{props.incident.commitments}</dd></div><div><dt>Current recommendation</dt><dd>Available</dd></div><div><dt>Human review</dt><dd>Required</dd></div></dl><button onClick={() => setInspectorTab('plans')}>Compare plans</button><button className="primary" onClick={() => setInspectorTab('decision')}>Review recommendation</button></aside>}
    {mode === 'docked' && <footer className="ask-docked-footer"><button onClick={props.onShowEvidence}>View evidence <span>{evidence.filter(item => item.status !== 'Restricted').length}</span></button><button onClick={props.onComparePlans}>Compare plans</button><button onClick={() => changeMode('expanded')}>Expand <Expand size={13}/></button></footer>}
  </section></div>;
}
