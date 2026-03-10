import styles from './MetricCard.module.css';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
}

const trendStyles: Record<string, string> = {
  up: styles.trendUp,
  down: styles.trendDown,
  neutral: styles.trendNeutral,
};

const trendArrows: Record<string, string> = {
  up: '▲',
  down: '▼',
  neutral: '—',
};

export default function MetricCard({
  title,
  value,
  subtitle,
  trend,
  trendValue,
}: MetricCardProps) {
  return (
    <div className={styles.card}>
      <p className={styles.title}>{title}</p>
      <div className={styles.valueRow}>
        <p className={styles.value}>{value}</p>
        {trend && trendValue && (
          <span className={`${styles.trend} ${trendStyles[trend]}`}>
            {trendArrows[trend]} {trendValue}
          </span>
        )}
      </div>
      {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
    </div>
  );
}
