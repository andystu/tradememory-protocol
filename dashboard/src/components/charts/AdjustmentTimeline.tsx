import type { AdjustmentEvent } from '../../api/types';
import styles from './AdjustmentTimeline.module.css';

interface AdjustmentTimelineProps {
  adjustments: AdjustmentEvent[];
}

const dotStyles: Record<string, string> = {
  applied: styles.dotApplied,
  proposed: styles.dotProposed,
  rejected: styles.dotRejected,
};

const badgeStyles: Record<string, string> = {
  applied: styles.badgeApplied,
  proposed: styles.badgeProposed,
  rejected: styles.badgeRejected,
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function AdjustmentTimeline({ adjustments }: AdjustmentTimelineProps) {
  // Sort most recent first
  const sorted = [...adjustments].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return (
    <div className={styles.timeline}>
      {sorted.map((adj) => (
        <div key={adj.id} className={styles.node}>
          <div className={`${styles.dot} ${dotStyles[adj.status] || styles.dotApplied}`} />
          <p className={styles.date}>{formatDate(adj.timestamp)}</p>
          <div className={styles.paramRow}>
            <span className={styles.paramName}>{adj.parameter}</span>
            <span className={styles.paramChange}>
              {adj.old_value} → {adj.new_value}
            </span>
            <span className={`${styles.badge} ${badgeStyles[adj.status] || styles.badgeApplied}`}>
              {adj.status}
            </span>
          </div>
          <p className={styles.reason}>{adj.reason}</p>
        </div>
      ))}
    </div>
  );
}
