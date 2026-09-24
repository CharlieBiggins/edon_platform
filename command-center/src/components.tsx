import { useEffect, useRef, type ReactNode } from 'react';
import { ArrowUpRight, CircleCheck, FileSearch, LockKeyhole, X } from 'lucide-react';
import type { Tone } from './types';

export function Badge({ children, tone = 'neutral', dot = false }: { children: ReactNode; tone?: Tone; dot?: boolean }) {
  return <span className={`badge ${tone}`}>{dot && <span className="status-dot" />}{children}</span>;
}
export function Panel({ title, eyebrow, action, children, className = '' }: { title: string; eyebrow?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}><div className="panel-heading"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h2>{title}</h2></div>{action}</div>{children}</section>;
}
export function Metric({ label, value, detail, tone = 'neutral' }: { label: string; value: string; detail: string; tone?: Tone }) {
  return <div className={`metric metric-${tone}`}><div className="metric-label">{label}</div><strong>{value}</strong><span>{detail}</span></div>;
}
export function EmptyState({ title, description, action, restricted = false }: { title: string; description: string; action?: ReactNode; restricted?: boolean }) {
  return <div className="empty-state">{restricted ? <LockKeyhole size={28} /> : <FileSearch size={30} />}<h2>{title}</h2><p>{description}</p>{action}</div>;
}
export function Modal({ title, children, onClose, wide = false }: { title: string; children: ReactNode; onClose: () => void; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { const dialog = ref.current!; const previous = document.activeElement as HTMLElement; dialog.showModal(); return () => { dialog.close(); previous?.focus(); }; }, []);
  return <dialog ref={ref} className={`modal ${wide ? 'wide' : ''}`} aria-label={title} onCancel={onClose}><div className="modal-heading"><div><div className="eyebrow">SIMULATED WORKFLOW</div><h2>{title}</h2></div><button className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={20} /></button></div>{children}</dialog>;
}
export function DefinitionList({ rows }: { rows: [string, ReactNode][] }) {
  return <dl className="definition-list">{rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}
export function TextLink({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return <button className="text-link" onClick={onClick}>{children}<ArrowUpRight size={14} /></button>;
}
export function Notice({ title, children, tone = 'amber' }: { title: string; children?: ReactNode; tone?: Tone }) {
  return <div className={`notice ${tone}`}><CircleCheck size={17} aria-hidden="true" /><div><strong>{title}</strong>{children && <div className="notice-body">{children}</div>}</div></div>;
}
export function LoadingState() {
  return <div role="status" aria-label="Loading simulated workspace" className="loading-state"><div className="skeleton title-skeleton" /><div className="metrics-grid">{[1, 2, 3, 4].map(i => <div key={i} className="skeleton metric-skeleton" />)}</div><div className="skeleton content-skeleton" /><p>Synchronizing simulated institutional state…</p></div>;
}
export function downloadFile(filename: string, body: string, type = 'application/json') {
  const url = URL.createObjectURL(new Blob([body], { type }));
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
