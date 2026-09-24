import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Badge, EmptyState, LoadingState, Notice, Panel } from './components';

describe('governed UI primitives', () => {
  it('renders status without relying on color alone', () => {
    render(<Badge tone="amber" dot>Review required</Badge>);
    expect(screen.getByText('Review required')).toBeVisible();
    expect(screen.getByText('Review required').className).toContain('badge');
    expect(document.querySelector('.status-dot')).toBeTruthy();
  });

  it('exposes loading as a live region', () => {
    render(<LoadingState />);
    expect(screen.getByRole('status', { name: 'Loading simulated workspace' })).toBeVisible();
  });

  it('renders explicit empty and restricted states', () => {
    render(<EmptyState title="No accessible evidence" description="Your role has no records in this scope." restricted />);
    expect(screen.getByRole('heading', { name: 'No accessible evidence' })).toBeVisible();
    expect(screen.getByText('Your role has no records in this scope.')).toBeVisible();
  });

  it('keeps notice semantics available to assistive technology', () => {
    render(<Notice title="Disconnected">Reconnect to refresh state.</Notice>);
    expect(screen.getByText('Disconnected')).toBeVisible();
    expect(screen.getByText('Reconnect to refresh state.')).toBeVisible();
  });

  it('composes a labelled panel', () => {
    render(<Panel eyebrow="ASSURE" title="Decision receipt">Receipt details</Panel>);
    expect(screen.getByRole('heading', { name: 'Decision receipt' })).toBeVisible();
    expect(screen.getByText('Receipt details')).toBeVisible();
  });
});
