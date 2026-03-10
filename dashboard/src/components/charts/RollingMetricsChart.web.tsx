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

export interface RollingMetricsWebProps {
  data: {
    date: string;
    profitFactor: number;
    winRate: number;
    avgR: number;
  }[];
}

export default function RollingMetricsChartWeb({ data }: RollingMetricsWebProps) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(26, 26, 40, 0.5)" />
        <XAxis
          dataKey="date"
          tick={{ fill: '#6a6a80', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
          tickLine={{ stroke: '#1a1a28' }}
          axisLine={{ stroke: '#1a1a28' }}
        />
        <YAxis
          yAxisId="left"
          tick={{ fill: '#6a6a80', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
          tickLine={{ stroke: '#1a1a28' }}
          axisLine={{ stroke: '#1a1a28' }}
        />
        <YAxis
          yAxisId="right"
          orientation="right"
          domain={[0, 100]}
          tick={{ fill: '#6a6a80', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
          tickLine={{ stroke: '#1a1a28' }}
          axisLine={{ stroke: '#1a1a28' }}
          tickFormatter={(v: number) => `${v}%`}
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
          yAxisId="left"
          type="monotone"
          dataKey="profitFactor"
          name="Profit Factor"
          stroke="#00e5ff"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: '#00e5ff' }}
        />
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="winRate"
          name="Win Rate %"
          stroke="#00ff88"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: '#00ff88' }}
        />
        <Line
          yAxisId="left"
          type="monotone"
          dataKey="avgR"
          name="Avg R"
          stroke="#ffaa00"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: '#ffaa00' }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
