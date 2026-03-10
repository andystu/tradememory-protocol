import styles from './Skeleton.module.css';

interface SkeletonProps {
  variant: 'card' | 'chart' | 'text';
  lines?: number;
}

export default function Skeleton({ variant, lines = 4 }: SkeletonProps) {
  if (variant === 'text') {
    return (
      <div className={styles.text}>
        {Array.from({ length: lines }).map((_, i) => (
          <div key={i} className={styles.textLine} />
        ))}
      </div>
    );
  }

  return <div className={styles[variant]} />;
}
