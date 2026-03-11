import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/layout/PageShell';
import Skeleton from '../components/ui/Skeleton';
import ErrorState from '../components/ui/ErrorState';
import EmptyState from '../components/ui/EmptyState';
import MemoryGrowth from '../components/charts/MemoryGrowth';
import OWMScoreTrend from '../components/charts/OWMScoreTrend';
import ConfidenceCalibration from '../components/charts/ConfidenceCalibration';
import ResonanceGauge from '../components/charts/ResonanceGauge';
import BayesianBeliefs from '../components/cards/BayesianBeliefs';
import { useMemoryGrowth, useOWMScoreTrend, useConfidenceCal, useBeliefs } from '../api/hooks';
import { useScrollReveal } from '../hooks/useScrollReveal';
import { formatRelativeTime } from '../utils/formatRelativeTime';
import styles from './IntelligencePage.module.css';

function RevealDiv({ children, className }: { children: React.ReactNode; className?: string }) {
  const { ref, isVisible } = useScrollReveal();
  return (
    <div ref={ref} className={`reveal ${isVisible ? 'visible' : ''} ${className ?? ''}`}>
      {children}
    </div>
  );
}

export default function IntelligencePage() {
  const { t } = useTranslation();
  const growth = useMemoryGrowth();
  const owm = useOWMScoreTrend();
  const cal = useConfidenceCal();
  const beliefs = useBeliefs();
  const [fetchedAt] = useState(() => new Date());

  // Compute resonance from calibration data
  const negativeRatio = cal.data && cal.data.length > 0
    ? cal.data.filter((p) => p.actual_pnl_r < 0).length / cal.data.length
    : 0;

  return (
    <PageShell>
      <div className={`${styles.page} pageFadeIn`}>
        <span className="lastUpdated">{formatRelativeTime(fetchedAt)}</span>

        {/* Row 1: Memory Growth — full width */}
        <RevealDiv className={styles.section}>
          <p className={styles.sectionTitle}>{t('intelligence.memoryGrowth')}</p>
          {growth.isLoading && <Skeleton variant="chart" />}
          {growth.error && (
            <ErrorState message={t('common.error')} onRetry={growth.mutate} />
          )}
          {!growth.isLoading && !growth.error && (!growth.data || growth.data.length === 0) && (
            <EmptyState
              icon="&#129504;"
              title={t('common.empty')}
              description="Store trades via MCP tools to see memory growth across regimes."
            />
          )}
          {!growth.isLoading && !growth.error && growth.data && growth.data.length > 0 && (
            <MemoryGrowth data={growth.data} />
          )}
        </RevealDiv>

        {/* Row 2: OWM Score Trend + Confidence Calibration */}
        <div className={styles.grid}>
          <RevealDiv className={styles.section}>
            <p className={styles.sectionTitle}>{t('intelligence.owmScoreTrend')}</p>
            {owm.isLoading && <Skeleton variant="chart" />}
            {owm.error && (
              <ErrorState message={t('common.error')} onRetry={owm.mutate} />
            )}
            {!owm.isLoading && !owm.error && (!owm.data || owm.data.length === 0) && (
              <EmptyState
                icon="&#128202;"
                title={t('common.empty')}
                description="Use the recall MCP tool to generate score history."
              />
            )}
            {!owm.isLoading && !owm.error && owm.data && owm.data.length > 0 && (
              <OWMScoreTrend data={owm.data} />
            )}
          </RevealDiv>

          <RevealDiv className={styles.section}>
            <p className={styles.sectionTitle}>{t('intelligence.confidenceCalibration')}</p>
            {cal.isLoading && <Skeleton variant="chart" />}
            {cal.error && (
              <ErrorState message={t('common.error')} onRetry={cal.mutate} />
            )}
            {!cal.isLoading && !cal.error && (!cal.data || cal.data.length === 0) && (
              <EmptyState
                icon="&#127919;"
                title={t('common.empty')}
                description="Trades with entry_confidence and R-multiple will appear here."
              />
            )}
            {!cal.isLoading && !cal.error && cal.data && cal.data.length > 0 && (
              <ConfidenceCalibration data={cal.data} />
            )}
          </RevealDiv>
        </div>

        {/* Row 3: Resonance Gauge + Bayesian Beliefs */}
        <div className={styles.grid}>
          <RevealDiv className={styles.section}>
            <p className={styles.sectionTitle}>{t('intelligence.resonanceRisk')}</p>
            {cal.isLoading && <Skeleton variant="card" />}
            {cal.error && (
              <ErrorState message={t('common.error')} onRetry={cal.mutate} />
            )}
            {!cal.isLoading && !cal.error && (!cal.data || cal.data.length === 0) && (
              <EmptyState
                icon="&#128308;"
                title={t('common.empty')}
                description="Needs calibration data to calculate resonance risk."
              />
            )}
            {!cal.isLoading && !cal.error && cal.data && cal.data.length > 0 && (
              <ResonanceGauge negativeRatio={negativeRatio} />
            )}
          </RevealDiv>

          <RevealDiv className={styles.section}>
            <p className={styles.sectionTitle}>{t('intelligence.bayesianBeliefs')}</p>
            {beliefs.isLoading && <Skeleton variant="chart" />}
            {beliefs.error && (
              <ErrorState message={t('common.error')} onRetry={beliefs.mutate} />
            )}
            {!beliefs.isLoading && !beliefs.error && (!beliefs.data || beliefs.data.length === 0) && (
              <EmptyState
                icon="&#129504;"
                title={t('common.empty')}
                description="Beliefs are generated from pattern discovery in L2 memory layer."
              />
            )}
            {!beliefs.isLoading && !beliefs.error && beliefs.data && beliefs.data.length > 0 && (
              <BayesianBeliefs data={beliefs.data} />
            )}
          </RevealDiv>
        </div>
      </div>
    </PageShell>
  );
}
