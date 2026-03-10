import type { MemoryGrowthPoint } from '../../api/types';
import MemoryGrowthWeb from './MemoryGrowth.web';

export interface MemoryGrowthProps {
  data: MemoryGrowthPoint[];
}

const REGIMES = ['trending_up', 'trending_down', 'ranging', 'volatile', 'unknown'] as const;

/**
 * Detect regimes with zero total memories across all data points.
 * Business logic only — no chart library imports.
 */
function detectBlindSpots(data: MemoryGrowthPoint[]): string[] {
  if (data.length === 0) return [];
  const last = data[data.length - 1];
  return REGIMES.filter((r) => last[r] === 0);
}

export default function MemoryGrowth({ data }: MemoryGrowthProps) {
  const blindSpots = detectBlindSpots(data);
  return <MemoryGrowthWeb data={data} blindSpots={blindSpots} />;
}
