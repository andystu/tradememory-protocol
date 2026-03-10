import type { BeliefState } from '../../api/types';
import styles from './BayesianBeliefs.module.css';

export interface BayesianBeliefsProps {
  data: BeliefState[];
}

const TREND_ICONS: Record<string, { symbol: string; className: string }> = {
  strengthening: { symbol: '\u25B2', className: 'trendUp' },
  strong: { symbol: '\u25B2', className: 'trendUp' },
  weakening: { symbol: '\u25BC', className: 'trendDown' },
  stable: { symbol: '\u2014', className: 'trendNeutral' },
  uncertain: { symbol: '\u2014', className: 'trendNeutral' },
};

export default function BayesianBeliefs({ data }: BayesianBeliefsProps) {
  const sorted = [...data]
    .sort((a, b) => b.sample_size - a.sample_size)
    .slice(0, 8);

  return (
    <div className={styles.grid}>
      {sorted.map((belief) => {
        const trend = TREND_ICONS[belief.trend] ?? TREND_ICONS.stable;
        const barWidth = belief.confidence * 100;

        return (
          <div key={belief.id} className={styles.card}>
            <div className={styles.header}>
              <p className={styles.proposition}>{belief.proposition}</p>
              <span className={`${styles.trendIcon} ${styles[trend.className]}`}>
                {trend.symbol}
              </span>
            </div>
            <div className={styles.barTrack}>
              <div
                className={styles.barFill}
                style={{ '--bar-width': `${barWidth}%` } as React.CSSProperties}
              />
            </div>
            <div className={styles.meta}>
              <span className={styles.confidence}>
                {(belief.confidence * 100).toFixed(0)}%
              </span>
              <span className={styles.sampleBadge}>
                n={belief.sample_size}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
