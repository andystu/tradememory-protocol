import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/layout/PageShell';
import Skeleton from '../components/ui/Skeleton';
import ErrorState from '../components/ui/ErrorState';
import EmptyState from '../components/ui/EmptyState';
import DreamComparison from '../components/charts/DreamComparison';
import { useDreamResults } from '../api/hooks';
import { useScrollReveal } from '../hooks/useScrollReveal';
import { formatRelativeTime } from '../utils/formatRelativeTime';
import styles from './DreamsPage.module.css';

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
  return value >= 999 ? '\u221E' : value.toFixed(2);
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
  const { t } = useTranslation();
  const { data, error, isLoading, mutate } = useDreamResults();
  const [fetchedAt] = useState(() => new Date());

  const CONDITION_LABELS: Record<string, string> = {
    no_memory: t('dreams.noMemory'),
    naive_recall: t('dreams.naiveRecall'),
    hybrid_recall: t('dreams.hybridRecall'),
  };

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
        <ErrorState message={t('common.error')} onRetry={() => mutate()} />
      </PageShell>
    );
  }

  if (!data || data.length === 0) {
    return (
      <PageShell>
        <EmptyState
          icon="&#128173;"
          title={t('common.empty')}
          description={t('dreams.noDreams')}
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
          <p className={styles.sectionTitle}>{t('dreams.dreamComparison')}</p>
          <div className={styles.chartContainer}>
            <DreamComparison data={data} />
          </div>
          <div className={styles.resonanceNote}>
            <span className={styles.resonanceBadge}>{t('dreams.resonance').toUpperCase()}</span>
            Parametric-External Memory Resonance: naive recall can HURT agent performance.
            Hybrid recall with ensure_negative_balance mitigates this risk.
          </div>
        </RevealDiv>

        {/* Session Table */}
        <RevealDiv className={styles.section}>
          <p className={styles.sectionTitle}>{t('dreams.dreamSessions')}</p>
          <div className={styles.tableWrap}>
            <table className={styles.dreamTable}>
              <thead>
                <tr>
                  <th>{t('strategies.date')}</th>
                  <th>{t('dreams.condition')}</th>
                  <th>{t('dreams.trades')}</th>
                  <th>PF</th>
                  <th>{t('strategies.pnl')}</th>
                  <th>WR</th>
                  <th>{t('dreams.resonance')}</th>
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
