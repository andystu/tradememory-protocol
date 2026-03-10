import ResonanceGaugeWeb from './ResonanceGauge.web';

export interface ResonanceGaugeProps {
  negativeRatio: number;
}

export type RiskLevel = 'good' | 'warning' | 'danger';

/**
 * Determine risk level from negative resonance ratio.
 * Business logic only — no chart library imports.
 */
function getRiskLevel(negativeRatio: number): RiskLevel {
  if (negativeRatio < 0.2) return 'good';
  if (negativeRatio <= 0.3) return 'warning';
  return 'danger';
}

export default function ResonanceGauge({ negativeRatio }: ResonanceGaugeProps) {
  const riskLevel = getRiskLevel(negativeRatio);
  return (
    <ResonanceGaugeWeb
      negativeRatio={negativeRatio}
      riskLevel={riskLevel}
    />
  );
}
