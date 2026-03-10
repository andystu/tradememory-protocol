import type { CalibrationPoint } from '../../api/types';
import ConfidenceCalibrationWeb from './ConfidenceCalibration.web';

export interface ConfidenceCalibrationProps {
  data: CalibrationPoint[];
}

export interface CalibrationChartPoint {
  entry_confidence: number;
  actual_pnl_r: number;
  trade_id: string;
  strategy: string;
  fill: string;
}

const STRATEGY_COLORS: Record<string, string> = {
  VolBreakout: '#00e5ff',
  IntradayMomentum: '#00ff88',
  Pullback: '#ffaa00',
};

/**
 * Transform calibration data into chart-ready format with strategy colors.
 * Business logic only — no chart library imports.
 */
function transformData(data: CalibrationPoint[]): CalibrationChartPoint[] {
  return data.map((p) => ({
    entry_confidence: p.entry_confidence,
    actual_pnl_r: p.actual_pnl_r,
    trade_id: p.trade_id,
    strategy: p.strategy,
    fill: STRATEGY_COLORS[p.strategy] ?? '#6a6a80',
  }));
}

export default function ConfidenceCalibration({ data }: ConfidenceCalibrationProps) {
  const chartData = transformData(data);
  return <ConfidenceCalibrationWeb data={chartData} />;
}
