import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Legend,
  Cell,
} from 'recharts';
import ChartTooltip from '../ui/ChartTooltip';
import type { CalibrationChartPoint } from './ConfidenceCalibration';

export interface ConfidenceCalibrationWebProps {
  data: CalibrationChartPoint[];
}

const STRATEGIES = [
  { name: 'VolBreakout', color: '#00e5ff' },
  { name: 'IntradayMomentum', color: '#00ff88' },
  { name: 'Pullback', color: '#ffaa00' },
];

function CalibrationTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: CalibrationChartPoint }> }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const entries = [
    { name: 'Strategy', value: 0, color: d.fill },
    { name: 'Confidence', value: d.entry_confidence, color: 'var(--cyan)' },
    { name: 'R-Multiple', value: d.actual_pnl_r, color: d.actual_pnl_r >= 0 ? 'var(--green)' : 'var(--red)' },
  ];
  return (
    <ChartTooltip
      active
      label={`${d.trade_id} — ${d.strategy}`}
      payload={entries}
      formatValue={(v, name) => {
        if (name === 'Strategy') return d.strategy;
        if (name === 'Confidence') return v.toFixed(2);
        return `${v.toFixed(2)}R`;
      }}
    />
  );
}

export default function ConfidenceCalibrationWeb({ data }: ConfidenceCalibrationWebProps) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <ScatterChart margin={{ top: 8, right: 16, bottom: 16, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(26, 26, 40, 0.5)" />
        <XAxis
          dataKey="entry_confidence"
          type="number"
          domain={[0, 1]}
          name="Entry Confidence"
          tick={{ fill: '#6a6a80', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
          tickLine={{ stroke: '#1a1a28' }}
          axisLine={{ stroke: '#1a1a28' }}
          label={{
            value: 'Entry Confidence',
            position: 'insideBottom',
            offset: -8,
            fill: '#6a6a80',
            fontSize: 11,
          }}
        />
        <YAxis
          dataKey="actual_pnl_r"
          type="number"
          name="R-Multiple"
          tick={{ fill: '#6a6a80', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
          tickLine={{ stroke: '#1a1a28' }}
          axisLine={{ stroke: '#1a1a28' }}
          label={{
            value: 'Actual R-Multiple',
            angle: -90,
            position: 'insideLeft',
            offset: 10,
            fill: '#6a6a80',
            fontSize: 11,
          }}
        />
        <Tooltip content={<CalibrationTooltip />} />
        <Legend
          content={() => (
            <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', paddingTop: '4px' }}>
              {STRATEGIES.map((s) => (
                <span key={s.name} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: '#6a6a80' }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: s.color, display: 'inline-block' }} />
                  {s.name}
                </span>
              ))}
            </div>
          )}
        />
        <ReferenceLine
          segment={[
            { x: 0, y: 0 },
            { x: 1, y: 2 },
          ]}
          stroke="#6a6a80"
          strokeDasharray="6 3"
          strokeWidth={1}
          label={{
            value: 'Perfect Calibration',
            position: 'insideTopRight',
            fill: '#6a6a80',
            fontSize: 10,
          }}
        />
        <Scatter data={data} fill="#00e5ff">
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.fill} />
          ))}
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
  );
}
