import { useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import ChartTooltip from '../ui/ChartTooltip';
import type { OWMScorePoint } from '../../api/types';
import styles from './OWMScoreTrend.module.css';

export interface OWMScoreTrendWebProps {
  data: OWMScorePoint[];
}

const COMPONENTS = [
  { key: 'avg_q', name: 'Quality', color: '#00ff88' },
  { key: 'avg_sim', name: 'Similarity', color: '#ffaa00' },
  { key: 'avg_rec', name: 'Recency', color: '#a855f7' },
  { key: 'avg_conf', name: 'Confidence', color: '#3b82f6' },
  { key: 'avg_aff', name: 'Affinity', color: '#ec4899' },
] as const;

export default function OWMScoreTrendWeb({ data }: OWMScoreTrendWebProps) {
  const [visible, setVisible] = useState<Record<string, boolean>>({
    avg_q: false,
    avg_sim: false,
    avg_rec: false,
    avg_conf: false,
    avg_aff: false,
  });

  const toggleComponent = (key: string) => {
    setVisible((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div>
      <div className={styles.toggleRow}>
        {COMPONENTS.map((c) => (
          <label key={c.key} className={styles.toggle}>
            <input
              type="checkbox"
              checked={visible[c.key]}
              onChange={() => toggleComponent(c.key)}
            />
            <span className={styles.toggleLabel} style={{ '--toggle-color': c.color } as React.CSSProperties}>
              {c.name}
            </span>
          </label>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(26, 26, 40, 0.5)" />
          <XAxis
            dataKey="date"
            angle={-35}
            textAnchor="end"
            height={60}
            interval="preserveStartEnd"
            tickFormatter={(v: string) => v.slice(5)}
            tick={{ fill: '#6a6a80', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
            tickLine={{ stroke: '#1a1a28' }}
            axisLine={{ stroke: '#1a1a28' }}
          />
          <YAxis
            domain={[0, 1]}
            tick={{ fill: '#6a6a80', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
            tickLine={{ stroke: '#1a1a28' }}
            axisLine={{ stroke: '#1a1a28' }}
          />
          <Tooltip content={<ChartTooltip />} />
          <Legend
            wrapperStyle={{
              color: '#6a6a80',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12,
            }}
          />
          <Line
            type="monotone"
            dataKey="avg_total"
            name="Total OWM"
            stroke="#00e5ff"
            strokeWidth={3}
            dot={false}
            activeDot={{ r: 4, fill: '#00e5ff' }}
          />
          {COMPONENTS.map((c) =>
            visible[c.key] ? (
              <Line
                key={c.key}
                type="monotone"
                dataKey={c.key}
                name={c.name}
                stroke={c.color}
                strokeWidth={1.5}
                strokeDasharray="4 2"
                dot={false}
                activeDot={{ r: 3, fill: c.color }}
              />
            ) : null,
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
