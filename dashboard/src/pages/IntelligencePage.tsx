import { useState } from 'react';
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
          <p className={styles.sectionTitle}>Memory Growth by Regime</p>
          {growth.isLoading && <Skeleton variant="chart" />}
          {growth.error && (
            <ErrorState message="Failed to load memory growth" onRetry={growth.mutate} />
          )}
          {!growth.isLoading && !growth.error && (!growth.data || growth.data.length === 0) && (
            <EmptyState
              icon="&#129504;"
              title="No memory data yet"
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
            <p className={styles.sectionTitle}>OWM Score Trend</p>
            {owm.isLoading && <Skeleton variant="chart" />}
            {owm.error && (
              <ErrorState message="Failed to load OWM scores" onRetry={owm.mutate} />
            )}
            {!owm.isLoading && !owm.error && (!owm.data || owm.data.length === 0) && (
              <EmptyState
                icon="&#128202;"
                title="No OWM recall data"
                description="Use the recall MCP tool to generate score history."
              />
            )}
            {!owm.isLoading && !owm.error && owm.data && owm.data.length > 0 && (
              <OWMScoreTrend data={owm.data} />
            )}
          </RevealDiv>

          <RevealDiv className={styles.section}>
            <p className={styles.sectionTitle}>Confidence Calibration</p>
            {cal.isLoading && <Skeleton variant="chart" />}
            {cal.error && (
              <ErrorState message="Failed to load calibration data" onRetry={cal.mutate} />
            )}
            {!cal.isLoading && !cal.error && (!cal.data || cal.data.length === 0) && (
              <EmptyState
                icon="&#127919;"
                title="No calibration data"
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
            <p className={styles.sectionTitle}>Resonance Risk</p>
            {cal.isLoading && <Skeleton variant="card" />}
            {cal.error && (
              <ErrorState message="Failed to load resonance data" onRetry={cal.mutate} />
            )}
            {!cal.isLoading && !cal.error && (!cal.data || cal.data.length === 0) && (
              <EmptyState
                icon="&#128308;"
                title="No resonance data"
                description="Needs calibration data to calculate resonance risk."
              />
            )}
            {!cal.isLoading && !cal.error && cal.data && cal.data.length > 0 && (
              <ResonanceGauge negativeRatio={negativeRatio} />
            )}
          </RevealDiv>

          <RevealDiv className={styles.section}>
            <p className={styles.sectionTitle}>Bayesian Beliefs</p>
            {beliefs.isLoading && <Skeleton variant="chart" />}
            {beliefs.error && (
              <ErrorState message="Failed to load beliefs" onRetry={beliefs.mutate} />
            )}
            {!beliefs.isLoading && !beliefs.error && (!beliefs.data || beliefs.data.length === 0) && (
              <EmptyState
                icon="&#129504;"
                title="No beliefs formed yet"
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
