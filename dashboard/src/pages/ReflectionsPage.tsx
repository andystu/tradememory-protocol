import { useState } from 'react';
import PageShell from '../components/layout/PageShell';
import Skeleton from '../components/ui/Skeleton';
import ErrorState from '../components/ui/ErrorState';
import EmptyState from '../components/ui/EmptyState';
import ReflectionCard from '../components/cards/ReflectionCard';
import { useReflections } from '../api/hooks';
import { useScrollReveal } from '../hooks/useScrollReveal';
import { downloadCSV } from '../utils/csvExport';
import { formatRelativeTime } from '../utils/formatRelativeTime';
import styles from './ReflectionsPage.module.css';

const DATE_RANGES = ['7d', '30d', '90d', 'All'] as const;
type DateRange = (typeof DATE_RANGES)[number];

const TYPE_TABS = [
  { key: 'daily', label: 'Daily', enabled: true },
  { key: 'weekly', label: 'Weekly', enabled: false },
  { key: 'monthly', label: 'Monthly', enabled: false },
] as const;

function RevealDiv({ children, className }: { children: React.ReactNode; className?: string }) {
  const { ref, isVisible } = useScrollReveal();
  return (
    <div ref={ref} className={`reveal ${isVisible ? 'visible' : ''} ${className ?? ''}`}>
      {children}
    </div>
  );
}

export default function ReflectionsPage() {
  const [dateRange, setDateRange] = useState<DateRange>('All');
  const [typeTab, setTypeTab] = useState('daily');
  const [fetchedAt] = useState(() => new Date());

  const params: Record<string, string> = {};
  if (dateRange !== 'All') {
    params.days = dateRange.replace('d', '');
  }
  if (typeTab !== 'daily') {
    params.type = typeTab;
  }

  const { data, error, isLoading, mutate } = useReflections(
    Object.keys(params).length > 0 ? params : undefined,
  );

  return (
    <PageShell>
      <div className={`${styles.page} pageFadeIn`}>
        {/* Controls */}
        <div className={styles.controls}>
          <div className={styles.dateButtons}>
            {DATE_RANGES.map((range) => (
              <button
                key={range}
                className={`${styles.dateBtn} ${dateRange === range ? styles.dateBtnActive : ''}`}
                onClick={() => setDateRange(range)}
              >
                {range}
              </button>
            ))}
          </div>
          <div className={styles.typeTabs}>
            {TYPE_TABS.map((tab) => (
              <button
                key={tab.key}
                className={`${styles.typeTab} ${typeTab === tab.key ? styles.typeTabActive : ''}`}
                disabled={!tab.enabled}
                onClick={() => tab.enabled && setTypeTab(tab.key)}
              >
                {tab.label}
                {!tab.enabled && <span className={styles.tooltip}>Coming soon</span>}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.metaRow}>
          <span className="lastUpdated">{formatRelativeTime(fetchedAt)}</span>
          {data && data.length > 0 && (
            <button
              className="csvExportBtn"
              onClick={() => {
                const today = new Date().toISOString().slice(0, 10);
                const exportData = data.map((r) => ({
                  date: r.date,
                  type: r.type,
                  grade: r.grade ?? '',
                  strategy: r.strategy ?? '',
                  summary: r.summary,
                }));
                downloadCSV(exportData, `reflections-${today}.csv`);
              }}
            >
              Export CSV
            </button>
          )}
        </div>

        {/* Content */}
        {isLoading && (
          <div className={styles.grid}>
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} variant="card" />
            ))}
          </div>
        )}

        {error && !isLoading && (
          <ErrorState
            message="Failed to load reflections"
            onRetry={() => mutate()}
          />
        )}

        {!isLoading && !error && (!data || data.length === 0) && (
          <EmptyState
            icon="&#128221;"
            title="No reflections yet"
            description="Run daily_review.py to generate AI-powered trade reviews."
          />
        )}

        {!isLoading && !error && data && data.length > 0 && (
          <div className={styles.grid}>
            {data.map((r) => (
              <RevealDiv key={`${r.date}-${r.strategy ?? 'all'}`}>
                <ReflectionCard reflection={r} />
              </RevealDiv>
            ))}
          </div>
        )}
      </div>
    </PageShell>
  );
}
