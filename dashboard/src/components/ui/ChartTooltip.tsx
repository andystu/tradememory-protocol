import styles from './ChartTooltip.module.css';

interface TooltipEntry {
  name?: string;
  value?: number;
  color?: string;
  dataKey?: string;
  payload?: Record<string, unknown>;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: TooltipEntry[];
  label?: string;
  formatValue?: (value: number, name: string) => string;
}

function defaultFormat(value: number, name: string): string {
  const lower = name.toLowerCase();
  if (lower.includes('pnl') || lower.includes('p&l') || lower.includes('equity') || lower.includes('dollar')) {
    return `$${value.toFixed(2)}`;
  }
  if (lower.includes('rate') || lower.includes('%') || lower.includes('percent') || lower.includes('wr')) {
    return `${value.toFixed(1)}%`;
  }
  if (lower.includes('r-mult') || lower.includes('avg r') || lower.includes('avgr')) {
    return `${value.toFixed(2)}R`;
  }
  if (lower.includes('pf') || lower.includes('profit factor')) {
    return value >= 999 ? '∞' : value.toFixed(2);
  }
  return typeof value === 'number' ? value.toFixed(2) : String(value);
}

export default function ChartTooltip({ active, payload, label, formatValue }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;

  const fmt = formatValue ?? defaultFormat;

  return (
    <div className={styles.tooltip}>
      {label != null && <p className={styles.label}>{label}</p>}
      {payload.map((entry, i) => (
        <div key={i} className={styles.row}>
          <span
            className={styles.dot}
            style={{ '--dot-color': entry.color ?? 'var(--cyan)' } as React.CSSProperties}
          />
          <span className={styles.name}>{entry.name}</span>
          <span className={styles.value}>{fmt(entry.value ?? 0, entry.name ?? '')}</span>
        </div>
      ))}
    </div>
  );
}
