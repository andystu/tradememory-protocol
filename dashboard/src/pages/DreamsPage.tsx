import { useState } from 'react';
import PageShell from '../components/layout/PageShell';
import Skeleton from '../components/ui/Skeleton';
import ErrorState from '../components/ui/ErrorState';
import EmptyState from '../components/ui/EmptyState';
import DreamComparison from '../components/charts/DreamComparison';
import { useDreamResults } from '../api/hooks';
import { useScrollReveal } from '../hooks/useScrollReveal';
import { formatRelativeTime } from '../utils/formatRelativeTime';
import styles from './DreamsPage.module.css';

const CONDITION_LABELS: Record<string, string> = {
  no_memory: 'No Memory',
  naive_recall: 'Naive Recall',
  hybrid_recall: 'Hybrid Recall',
};

const CONDITION_CLASS: Record<string, string> = {
  no_memory: styles.conditionNoMem,
  naive_recall: styles.conditionNaive,
  hybrid_recall: styles.conditionHybrid,
};

function formatPnl(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}$${value.toFixed(2)}`;
}

function formatPf(value: number): string {
  return value >= 999 ? '∞' : value.toFixed(2);
}

function RevealDiv({ children, className }: { children: React.ReactNode; className?: string }) {
  const { ref, isVisible } = useScrollReveal();
  return (
    <div ref={ref} className={`reveal ${isVisible ? 'visible' : ''} ${className ?? ''}`}>
      {children}
    </div>
  );
}

export default function DreamsPage() {
  const { data, error, isLoading, mutate } = useDreamResults();
  const [fetchedAt] = useState(() => new Date());

  if (isLoading) {
    return (
      <PageShell>
        <div className={`${styles.page} pageFadeIn`}>
          <Skeleton variant="chart" />
          <Skeleton variant="chart" />
        </div>
      </PageShell>
    );
  }

  if (error) {
    return (
      <PageShell>
        <ErrorState message="Failed to load dream results" onRetry={() => mutate()} />
      </PageShell>
    );
  }

  if (!data || data.length === 0) {
    return (
      <PageShell>
        <EmptyState
          icon="&#128173;"
          title="Trade Dreaming — Phase 2"
          description="A/B testing with 2000 hybrid recall trades is planned. This page will visualize the results."
        />
      </PageShell>
    );
  }

  return (
    <PageShell>
      <div className={`${styles.page} pageFadeIn`}>
        <span className="lastUpdated">{formatRelativeTime(fetchedAt)}</span>

        {/* Comparison Chart */}
        <RevealDiv className={styles.section}>
          <p className={styles.sectionTitle}>Dream Comparison — Profit Factor by Condition</p>
          <div className={styles.chartContainer}>
            <DreamComparison data={data} />
          </div>
          <div className={styles.resonanceNote}>
            <span className={styles.resonanceBadge}>RESONANCE</span>
            Parametric-External Memory Resonance: naive recall can HURT agent performance.
            Hybrid recall with ensure_negative_balance mitigates this risk.
          </div>
        </RevealDiv>

        {/* Session Table */}
        <RevealDiv className={styles.section}>
          <p className={styles.sectionTitle}>Dream Sessions</p>
          <div className={styles.tableWrap}>
            <table className={styles.dreamTable}>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Condition</th>
                  <th>Trades</th>
                  <th>PF</th>
                  <th>P&amp;L</th>
                  <th>WR</th>
                  <th>Resonance</th>
                </tr>
              </thead>
              <tbody>
                {data.map((session) => (
                  <tr key={session.id}>
                    <td>{new Date(session.timestamp).toLocaleDateString()}</td>
                    <td className={CONDITION_CLASS[session.condition] ?? ''}>
                      {CONDITION_LABELS[session.condition] ?? session.condition}
                    </td>
                    <td>{session.trades}</td>
                    <td>{formatPf(session.pf)}</td>
                    <td className={session.pnl >= 0 ? styles.pnlPos : styles.pnlNeg}>
                      {formatPnl(session.pnl)}
                    </td>
                    <td>{(session.wr * 100).toFixed(1)}%</td>
                    <td>
                      <span
                        className={`${styles.dot} ${session.resonance_detected ? styles.dotRed : styles.dotGreen}`}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </RevealDiv>
      </div>
    </PageShell>
  );
}
