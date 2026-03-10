import type { RollingMetricPoint } from '../../api/types';
import RollingMetricsChartWeb from './RollingMetricsChart.web';

export interface RollingMetricsChartProps {
  data: RollingMetricPoint[];
}

/**
 * Transform rolling metrics into chart-ready format.
 * Business logic only — no chart library imports.
 */
function transformData(data: RollingMetricPoint[]) {
  return data.map((p) => ({
    date: p.date,
    profitFactor: p.rolling_pf,
    winRate: Math.round(p.rolling_wr * 100),
    avgR: p.rolling_avg_r,
  }));
}

export default function RollingMetricsChart({ data }: RollingMetricsChartProps) {
  const chartData = transformData(data);
  return <RollingMetricsChartWeb data={chartData} />;
}
