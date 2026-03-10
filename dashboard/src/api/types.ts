/**
 * TypeScript interfaces matching backend Pydantic response models.
 * Source: src/tradememory/dashboard_models.py
 */

export interface OverviewResponse {
  total_trades: number;
  total_pnl: number;
  win_rate: number;
  profit_factor: number;
  current_equity: number;
  max_drawdown_pct: number;
  memory_count: number;
  avg_confidence: number;
  last_trade_date: string | null;
  strategies: string[];
}

export interface EquityPoint {
  date: string;
  cumulative_pnl: number;
  drawdown_pct: number;
  trade_count: number;
}

export interface RollingMetricPoint {
  date: string;
  rolling_pf: number;
  rolling_wr: number;
  rolling_avg_r: number;
  window_size: number;
}

export interface MemoryGrowthPoint {
  date: string;
  total_memories: number;
  trending_up: number;
  trending_down: number;
  ranging: number;
  volatile: number;
  unknown: number;
}

export interface OWMScorePoint {
  date: string;
  avg_total: number;
  avg_q: number;
  avg_sim: number;
  avg_rec: number;
  avg_conf: number;
  avg_aff: number;
  query_count: number;
}

export interface CalibrationPoint {
  trade_id: string;
  entry_confidence: number;
  actual_pnl_r: number;
  strategy: string;
}

export interface StrategyDetailResponse {
  name: string;
  total_trades: number;
  win_rate: number;
  profit_factor: number;
  avg_pnl_r: number;
  avg_hold_seconds: number;
  best_session: string;
  worst_session: string;
  baseline_pf: number;
  baseline_wr: number;
  trades: Record<string, unknown>[];
  session_heatmap: Record<string, unknown>[];
}

export interface ReflectionSummary {
  date: string;
  type: string;
  grade: string | null;
  strategy: string | null;
  summary: string;
  full_path: string;
}

export interface AdjustmentEvent {
  id: string;
  timestamp: string;
  adjustment_type: string;
  parameter: string;
  old_value: string;
  new_value: string;
  reason: string;
  status: string;
  strategy: string | null;
}

export interface BeliefState {
  id: string;
  proposition: string;
  alpha: number;
  beta: number;
  confidence: number;
  strategy: string | null;
  regime: string | null;
  sample_size: number;
  trend: string;
}

export interface DreamSession {
  id: string;
  timestamp: string;
  condition: string;
  trades: number;
  pf: number;
  pnl: number;
  wr: number;
  has_memory: boolean;
  memory_type: string | null;
  resonance_detected: boolean;
}
