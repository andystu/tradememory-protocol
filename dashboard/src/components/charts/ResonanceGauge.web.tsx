import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import type { RiskLevel } from './ResonanceGauge';
import styles from './ResonanceGauge.module.css';

export interface ResonanceGaugeWebProps {
  negativeRatio: number;
  riskLevel: RiskLevel;
}

const RISK_LABELS: Record<RiskLevel, string> = {
  good: 'Healthy',
  warning: 'Caution',
  danger: 'At Risk',
};

export default function ResonanceGaugeWeb({ negativeRatio, riskLevel }: ResonanceGaugeWebProps) {
  const pct = Math.round(negativeRatio * 100);
  const positiveRatio = 1 - negativeRatio;

  const data = [
    { name: 'Negative', value: negativeRatio },
    { name: 'Positive', value: positiveRatio },
  ];

  return (
    <div className={styles.container}>
      <div className={styles.chartWrap}>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              innerRadius={60}
              outerRadius={80}
              startAngle={90}
              endAngle={-270}
              paddingAngle={2}
            >
              <Cell fill="#ff3366" />
              <Cell fill="#00ff88" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className={styles.centerLabel}>
          <span className={styles.pctValue}>{pct}%</span>
          <span className={styles.pctSub}>negative</span>
        </div>
      </div>
      <div className={styles.footer}>
        <span className={`${styles.riskBadge} ${styles[riskLevel]}`}>
          {RISK_LABELS[riskLevel]}
        </span>
        <span className={styles.target}>Target: &lt;20%</span>
      </div>
      <p className={styles.label}>Resonance Risk</p>
    </div>
  );
}
