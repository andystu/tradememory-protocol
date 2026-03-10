import styles from './Sidebar.module.css';

type DateRange = '7d' | '30d' | '90d' | 'all';

interface SidebarProps {
  strategies: string[];
  dateRange: DateRange;
  onStrategyChange: (strategy: string, checked: boolean) => void;
  onDateRangeChange: (range: DateRange) => void;
}

const dateRangeOptions: { value: DateRange; label: string }[] = [
  { value: '7d', label: '7 Days' },
  { value: '30d', label: '30 Days' },
  { value: '90d', label: '90 Days' },
  { value: 'all', label: 'All Time' },
];

export default function Sidebar({
  strategies,
  dateRange,
  onStrategyChange,
  onDateRangeChange,
}: SidebarProps) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.section}>
        <p className={styles.sectionTitle}>Strategies</p>
        {strategies.map((strategy) => (
          <label key={strategy} className={styles.checkboxLabel}>
            <input
              type="checkbox"
              defaultChecked
              onChange={(e) => onStrategyChange(strategy, e.target.checked)}
            />
            {strategy}
          </label>
        ))}
      </div>
      <div className={styles.section}>
        <p className={styles.sectionTitle}>Date Range</p>
        {dateRangeOptions.map(({ value, label }) => (
          <label key={value} className={styles.radioLabel}>
            <input
              type="radio"
              name="dateRange"
              value={value}
              checked={dateRange === value}
              onChange={() => onDateRangeChange(value)}
            />
            {label}
          </label>
        ))}
      </div>
    </aside>
  );
}
