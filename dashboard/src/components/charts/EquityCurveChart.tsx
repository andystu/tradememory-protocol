import type { EquityPoint } from '../../api/types';
import EquityCurveChartWeb from './EquityCurveChart.web';

export interface EquityCurveChartProps {
  data: EquityPoint[];
}

/**
 * Transform raw equity points into chart-ready format.
 * Business logic only — no chart library imports.
 */
function transformData(data: EquityPoint[]) {
  return data.map((p) => ({
    time: p.date,
    value: p.cumulative_pnl,
    drawdown: p.drawdown_pct,
    trades: p.trade_count,
  }));
}

export default function EquityCurveChart({ data }: EquityCurveChartProps) {
  const chartData = transformData(data);
  return <EquityCurveChartWeb data={chartData} />;
}
