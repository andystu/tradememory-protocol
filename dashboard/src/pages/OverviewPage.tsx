import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/layout/PageShell';
import MetricCard from '../components/cards/MetricCard';
import Skeleton from '../components/ui/Skeleton';
import ErrorState from '../components/ui/ErrorState';
import EmptyState from '../components/ui/EmptyState';
import EquityCurveChart from '../components/charts/EquityCurveChart';
import RollingMetricsChart from '../components/charts/RollingMetricsChart';
import { useOverview, useEquityCurve, useRollingMetrics } from '../api/hooks';
import { useScrollReveal } from '../hooks/useScrollReveal';
import { downloadCSV } from '../utils/csvExport';
import { formatRelativeTime } from '../utils/formatRelativeTime';
import styles from './OverviewPage.module.css';

function formatPnl(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function RevealDiv({ children, className }: { children: React.ReactNode; className?: string }) {
  const { ref, isVisible } = useScrollReveal();
  return (
    <div ref={ref} className={`reveal ${isVisible ? 'visible' : ''} ${className ?? ''}`}>
      {children}
    </div>
  );
}

export default function OverviewPage() {
  const { t } = useTranslation();
  const overview = useOverview();
  const equity = useEquityCurve();
  const rolling = useRollingMetrics();
  const [fetchedAt] = useState(() => new Date());

  const isLoading = overview.isLoading || equity.isLoading || rolling.isLoading;
  const error = overview.error || equity.error || rolling.error;

  if (isLoading) {
    return (
      <PageShell>
        <div className={`${styles.page} pageFadeIn`}>
          <div className={styles.metricRow}>
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} variant="card" />
            ))}
          </div>
          <Skeleton variant="chart" />
          <Skeleton variant="chart" />
        </div>
      </PageShell>
    );
  }

  if (error) {
    return (
      <PageShell>
        <ErrorState
          message={t('common.error')}
          onRetry={() => {
            overview.mutate();
            equity.mutate();
            rolling.mutate();
          }}
        />
      </PageShell>
    );
  }

  if (!overview.data || overview.data.total_trades === 0) {
    return (
      <PageShell>
        <EmptyState
          icon="&#128200;"
          title={t('common.empty')}
          description="Store trades via MCP tools or REST API to see your overview dashboard."
        />
      </PageShell>
    );
  }

  const d = overview.data;

  return (
    <PageShell>
      <div className={`${styles.page} pageFadeIn`}>
        <span className="lastUpdated">{formatRelativeTime(fetchedAt)}</span>

        {/* Metric Cards */}
        <RevealDiv className={styles.metricRow}>
          <MetricCard
            title={t('overview.totalPnl')}
            value={formatPnl(d.total_pnl)}
            trend={d.total_pnl >= 0 ? 'up' : 'down'}
            trendValue={`${d.total_trades} ${t('overview.trades')}`}
          />
          <MetricCard
            title={t('overview.winRate')}
            value={formatPct(d.win_rate)}
            trend={d.win_rate >= 0.5 ? 'up' : 'down'}
            trendValue={`${Math.round(d.win_rate * d.total_trades)}W / ${d.total_trades - Math.round(d.win_rate * d.total_trades)}L`}
          />
          <MetricCard
            title={t('overview.profitFactor')}
            value={d.profit_factor.toFixed(2)}
            trend={d.profit_factor >= 1.5 ? 'up' : d.profit_factor >= 1.0 ? 'neutral' : 'down'}
            trendValue={d.profit_factor >= 1.5 ? t('overview.strong') : d.profit_factor >= 1.0 ? 'Marginal' : 'Losing'}
          />
          <MetricCard
            title={t('overview.maxDrawdown')}
            value={formatPct(d.max_drawdown_pct)}
            trend={d.max_drawdown_pct <= 0.05 ? 'up' : d.max_drawdown_pct <= 0.1 ? 'neutral' : 'down'}
            trendValue={`${t('overview.equity')}: $${d.current_equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
          />
          <MetricCard
            title={t('overview.memories')}
            value={d.memory_count}
            subtitle={`Avg confidence: ${formatPct(d.avg_confidence)}`}
          />
        </RevealDiv>

        {/* Equity Curve */}
        {equity.data && equity.data.length > 0 && (
          <RevealDiv className={styles.chartSection}>
            <div className="sectionHeader">
              <p className={styles.chartTitle}>{t('overview.equityCurve')}</p>
              <button
                className="csvExportBtn"
                onClick={() => {
                  const today = new Date().toISOString().slice(0, 10);
                  downloadCSV(equity.data as unknown as Record<string, unknown>[], `equity-curve-${today}.csv`);
                }}
              >
                {t('overview.exportCsv')}
              </button>
            </div>
            <div className={styles.chartContainer}>
              <EquityCurveChart data={equity.data} />
            </div>
          </RevealDiv>
        )}

        {/* Rolling Metrics */}
        {rolling.data && rolling.data.length > 0 && (
          <RevealDiv className={styles.chartSection}>
            <p className={styles.chartTitle}>{t('overview.rollingMetrics')}</p>
            <div className={styles.chartContainer}>
              <RollingMetricsChart data={rolling.data} />
            </div>
          </RevealDiv>
        )}
      </div>
    </PageShell>
  );
}
