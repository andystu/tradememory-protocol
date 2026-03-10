export interface HeatmapCell {
  session: string;
  day: string;
  trades: number;
  avg_pnl: number;
}

export interface StrategyHeatmapProps {
  data: HeatmapCell[];
}

const SESSIONS = ['Asia', 'London', 'New York', 'Overlap'];
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];

/**
 * Build a lookup map from heatmap data.
 * Business logic only — no rendering.
 */
export function buildHeatmapGrid(data: HeatmapCell[]) {
  const lookup = new Map<string, HeatmapCell>();
  let maxAbs = 0;

  for (const cell of data) {
    // Normalize session names (backend may use "NY" instead of "New York")
    const session = cell.session === 'NY' ? 'New York' : cell.session;
    const key = `${session}:${cell.day}`;
    lookup.set(key, { ...cell, session });
    const abs = Math.abs(cell.avg_pnl);
    if (abs > maxAbs) maxAbs = abs;
  }

  return { lookup, maxAbs, sessions: SESSIONS, days: DAYS };
}

export function getCellColor(avgPnl: number, maxAbs: number): string {
  if (maxAbs === 0) return 'rgba(255,255,255,0.05)';
  const intensity = Math.min(Math.abs(avgPnl) / maxAbs, 1);
  const alpha = 0.15 + intensity * 0.6;
  return avgPnl >= 0
    ? `rgba(0, 255, 136, ${alpha})`
    : `rgba(255, 51, 102, ${alpha})`;
}

export { default } from './StrategyHeatmap.web';
