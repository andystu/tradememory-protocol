import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import ChartTooltip from '../ui/ChartTooltip';
import type { MemoryGrowthPoint } from '../../api/types';

export interface MemoryGrowthWebProps {
  data: MemoryGrowthPoint[];
  blindSpots: string[];
}

const REGIME_CONFIG = [
  { key: 'trending_up', name: 'Trending Up', fill: '#00ff88', fillOpacity: 0.7 },
  { key: 'trending_down', name: 'Trending Down', fill: '#ff3366', fillOpacity: 0.7 },
  { key: 'ranging', name: 'Ranging', fill: '#ffaa00', fillOpacity: 0.7 },
  { key: 'volatile', name: 'Volatile', fill: '#00e5ff', fillOpacity: 0.7 },
  { key: 'unknown', name: 'Unknown', fill: '#444444', fillOpacity: 0.7 },
] as const;

export default function MemoryGrowthWeb({ data, blindSpots }: MemoryGrowthWebProps) {
  return (
    <div>
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(26, 26, 40, 0.5)" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#6a6a80', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
            tickLine={{ stroke: '#1a1a28' }}
            axisLine={{ stroke: '#1a1a28' }}
          />
          <YAxis
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
          {REGIME_CONFIG.map((regime) => (
            <Area
              key={regime.key}
              type="monotone"
              dataKey={regime.key}
              name={regime.name}
              stackId="regime"
              fill={regime.fill}
              fillOpacity={regime.fillOpacity}
              stroke={regime.fill}
              strokeWidth={1}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
      {blindSpots.length > 0 && (
        <div style={{ marginTop: '8px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {blindSpots.map((regime) => (
            <span
              key={regime}
              style={{
                background: 'rgba(255, 170, 0, 0.15)',
                color: '#ffaa00',
                padding: '4px 10px',
                borderRadius: '4px',
                fontSize: '0.75rem',
                fontFamily: "var(--font-mono)",
              }}
            >
              Blind spot: no {regime.replace('_', ' ')} memories
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
