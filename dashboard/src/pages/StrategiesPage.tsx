import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/layout/PageShell';
import MetricCard from '../components/cards/MetricCard';
import Skeleton from '../components/ui/Skeleton';
import ErrorState from '../components/ui/ErrorState';
import EmptyState from '../components/ui/EmptyState';
import StrategyHeatmap from '../components/charts/StrategyHeatmap';
import AdjustmentTimeline from '../components/charts/AdjustmentTimeline';
import { useStrategy, useAdjustments } from '../api/hooks';
import { useScrollReveal } from '../hooks/useScrollReveal';
import { downloadCSV } from '../utils/csvExport';
import { formatRelativeTime } from '../utils/formatRelativeTime';
import styles from './StrategiesPage.module.css';

const STRATEGIES = ['VolBreakout', 'IntradayMomentum', 'Pullback'] as const;
type StrategyName = typeof STRATEGIES[number];

const BASELINES: Record<StrategyName, { pf: number; wr: number }> = {
  VolBreakout: { pf: 1.17, wr: 0.55 },
  IntradayMomentum: { pf: 1.78, wr: 0.58 },
  Pullback: { pf: 1.45, wr: 0.52 },
};

const PAGE_SIZE = 20;

function formatPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatDelta(current: number, baseline: number, isPercent: boolean, vsLabel: string): { text: string; trend: 'up' | 'down' | 'neutral' } {
  const delta = current - baseline;
  if (Math.abs(delta) < 0.001) return { text: `= baseline`, trend: 'neutral' };
  const formatted = isPercent
    ? `${delta > 0 ? '+' : ''}${(delta * 100).toFixed(1)}pp`
    : `${delta > 0 ? '+' : ''}${delta.toFixed(2)}`;
  return { text: `${formatted} ${vsLabel}`, trend: delta > 0 ? 'up' : 'down' };
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function formatPnl(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}$${value.toFixed(2)}`;
}

function RevealDiv({ children, className }: { children: React.ReactNode; className?: string }) {
  const { ref, isVisible } = useScrollReveal();
  return (
    <div ref={ref} className={`reveal ${isVisible ? 'visible' : ''} ${className ?? ''}`}>
      {children}
    </div>
  );
}

export default function StrategiesPage() {
  const { t } = useTranslation();
  const [selected, setSelected] = useState<StrategyName>('VolBreakout');
  const [visibleRows, setVisibleRows] = useState(PAGE_SIZE);

  const strategy = useStrategy(selected);
  const adjustments = useAdjustments();
  const [fetchedAt] = useState(() => new Date());

  const isLoading = strategy.isLoading;
  const error = strategy.error;

  if (isLoading) {
    return (
      <PageShell>
        <div className={`${styles.page} pageFadeIn`}>
          <TabBar selected={selected} onSelect={(s) => { setSelected(s); setVisibleRows(PAGE_SIZE); }} />
          <div className={styles.metricRow}>
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} variant="card" />
            ))}
          </div>
          <div className={styles.twoCol}>
            <Skeleton variant="chart" />
            <Skeleton variant="chart" />
          </div>
          <Skeleton variant="chart" />
        </div>
      </PageShell>
    );
  }

  if (error) {
    return (
      <PageShell>
        <div className={`${styles.page} pageFadeIn`}>
          <TabBar selected={selected} onSelect={(s) => { setSelected(s); setVisibleRows(PAGE_SIZE); }} />
          <ErrorState
            message={t('common.error')}
            onRetry={() => { strategy.mutate(); adjustments.mutate(); }}
          />
        </div>
      </PageShell>
    );
  }

  if (!strategy.data || strategy.data.total_trades === 0) {
    return (
      <PageShell>
        <div className={`${styles.page} pageFadeIn`}>
          <TabBar selected={selected} onSelect={(s) => { setSelected(s); setVisibleRows(PAGE_SIZE); }} />
          <EmptyState
            icon="&#128640;"
            title={t('common.empty')}
            description="Store trades with a strategy tag to see performance breakdowns."
          />
        </div>
      </PageShell>
    );
  }

  const d = strategy.data;
  const baseline = BASELINES[selected];
  const wrDelta = formatDelta(d.win_rate, baseline.wr, true, t('strategies.vsBaseline'));
  const pfDelta = formatDelta(d.profit_factor, baseline.pf, false, t('strategies.vsBaseline'));

  // Filter adjustments for selected strategy
  const strategyAdjustments = (adjustments.data || []).filter(
    (a) => a.strategy === selected || a.strategy === null
  );

  // Sort trades by timestamp desc
  const trades = [...d.trades].sort(
    (a, b) => new Date(b.timestamp as string).getTime() - new Date(a.timestamp as string).getTime()
  );

  const visibleTrades = trades.slice(0, visibleRows);
  const hasMore = trades.length > visibleRows;

  return (
    <PageShell>
      <div className={`${styles.page} pageFadeIn`}>
        <TabBar selected={selected} onSelect={(s) => { setSelected(s); setVisibleRows(PAGE_SIZE); }} />
        <span className="lastUpdated">{formatRelativeTime(fetchedAt)}</span>

        {/* KPI Comparison */}
        <RevealDiv className={styles.metricRow}>
          <MetricCard
            title={t('strategies.winRate')}
            value={formatPct(d.win_rate)}
            trend={wrDelta.trend}
            trendValue={wrDelta.text}
          />
          <MetricCard
            title={t('strategies.profitFactor')}
            value={d.profit_factor.toFixed(2)}
            trend={pfDelta.trend}
            trendValue={pfDelta.text}
          />
          <MetricCard
            title={t('strategies.avgRMultiple')}
            value={d.avg_pnl_r.toFixed(2)}
            trend={d.avg_pnl_r >= 0.5 ? 'up' : d.avg_pnl_r >= 0 ? 'neutral' : 'down'}
            trendValue={d.avg_pnl_r >= 0.5 ? t('strategies.strongEdge') : d.avg_pnl_r >= 0 ? 'Marginal' : t('intelligence.negative')}
          />
          <MetricCard
            title={t('strategies.totalTrades')}
            value={d.total_trades}
            subtitle={`${t('common.best')}: ${d.best_session} · ${t('common.worst')}: ${d.worst_session}`}
          />
        </RevealDiv>

        {/* Heatmap + Timeline */}
        <div className={styles.twoCol}>
          <RevealDiv className={styles.section}>
            <p className={styles.sectionTitle}>{t('strategies.sessionDayHeatmap')}</p>
            {d.session_heatmap.length > 0 ? (
              <StrategyHeatmap data={d.session_heatmap as { session: string; day: string; trades: number; avg_pnl: number }[]} />
            ) : (
              <EmptyState icon="&#128200;" title={t('common.empty')} description="Trade data will populate the heatmap." />
            )}
          </RevealDiv>
          <RevealDiv className={styles.section}>
            <p className={styles.sectionTitle}>{t('strategies.adjustmentTimeline')}</p>
            {adjustments.isLoading ? (
              <Skeleton variant="chart" />
            ) : adjustments.error ? (
              <ErrorState message={t('common.error')} onRetry={() => adjustments.mutate()} />
            ) : strategyAdjustments.length > 0 ? (
              <AdjustmentTimeline adjustments={strategyAdjustments} />
            ) : (
              <EmptyState icon="&#128295;" title={t('common.empty')} description="Parameter changes will appear here." />
            )}
          </RevealDiv>
        </div>

        {/* Trade List */}
        <RevealDiv className={styles.section}>
          <div className="sectionHeader">
            <p className={styles.sectionTitle}>{t('strategies.recentTrades')}</p>
            {trades.length > 0 && (
              <button
                className="csvExportBtn"
                onClick={() => {
                  const today = new Date().toISOString().slice(0, 10);
                  downloadCSV(trades as Record<string, unknown>[], `trades-${selected}-${today}.csv`);
                }}
              >
                {t('overview.exportCsv')}
              </button>
            )}
          </div>
          <div className={styles.tableWrap}>
            <table className={styles.tradeTable}>
              <thead>
                <tr>
                  <th>{t('strategies.date')}</th>
                  <th>{t('strategies.direction')}</th>
                  <th>{t('strategies.session')}</th>
                  <th>{t('strategies.pnl')}</th>
                  <th>{t('strategies.rMult')}</th>
                  <th>{t('strategies.duration')}</th>
                </tr>
              </thead>
              <tbody>
                {visibleTrades.map((tr) => {
                  const trade = tr as Record<string, unknown>;
                  const pnl = (trade.pnl as number) ?? 0;
                  const pnlR = (trade.pnl_r as number) ?? 0;
                  const side = (trade.side as string) ?? (trade.direction as string) ?? '—';
                  const holdSec = ((trade.hold_seconds as number) ?? (trade.hold_duration as number)) ?? 0;
                  return (
                    <tr key={trade.id as string}>
                      <td>{((trade.date as string) ?? (trade.timestamp as string) ?? "").slice(0, 10)}</td>
                      <td className={(side === 'BUY' || side === 'LONG' || side === 'long') ? styles.long : styles.short}>
                        {(side === 'BUY' || side === 'LONG' || side === 'long') ? 'LONG' : (side === '—' ? '—' : 'SHORT')}
                      </td>
                      <td>{trade.session as string}</td>
                      <td className={pnl >= 0 ? styles.pnlPos : styles.pnlNeg}>
                        {formatPnl(pnl)}
                      </td>
                      <td className={pnlR >= 0 ? styles.pnlPos : styles.pnlNeg}>
                        {pnlR >= 0 ? '+' : ''}{pnlR.toFixed(2)}R
                      </td>
                      <td>{formatDuration(holdSec)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {hasMore && (
            <button
              className={styles.showMore}
              onClick={() => setVisibleRows((v) => v + PAGE_SIZE)}
            >
              Show more ({trades.length - visibleRows} remaining)
            </button>
          )}
        </RevealDiv>
      </div>
    </PageShell>
  );
}

/* Tab bar sub-component */
function TabBar({ selected, onSelect }: { selected: StrategyName; onSelect: (s: StrategyName) => void }) {
  return (
    <div className={styles.tabBar}>
      {STRATEGIES.map((name) => (
        <button
          key={name}
          className={`${styles.tab} ${selected === name ? styles.tabActive : ''}`}
          onClick={() => onSelect(name)}
        >
          {name}
        </button>
      ))}
    </div>
  );
}
