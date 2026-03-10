import { useState } from 'react';
import Markdown from 'react-markdown';
import type { ReflectionSummary } from '../../api/types';
import styles from './ReflectionCard.module.css';

const GRADE_CLASS: Record<string, string> = {
  A: styles.gradeA,
  B: styles.gradeB,
  C: styles.gradeC,
  D: styles.gradeD,
  F: styles.gradeF,
};

interface ReflectionCardProps {
  reflection: ReflectionSummary;
}

export default function ReflectionCard({ reflection }: ReflectionCardProps) {
  const [expanded, setExpanded] = useState(false);

  const gradeClass = reflection.grade ? GRADE_CLASS[reflection.grade] ?? '' : '';
  const displayText = expanded
    ? reflection.summary
    : reflection.summary.length > 160
      ? reflection.summary.slice(0, 160) + '...'
      : reflection.summary;

  return (
    <div
      className={`${styles.card} ${expanded ? styles.cardExpanded : ''}`}
      onClick={() => setExpanded((prev) => !prev)}
    >
      <div className={styles.header}>
        {reflection.grade && (
          <span className={`${styles.gradeBadge} ${gradeClass}`}>
            {reflection.grade}
          </span>
        )}
        <div className={styles.headerInfo}>
          <p className={styles.date}>{reflection.date}</p>
          {reflection.strategy && (
            <span className={styles.strategy}>{reflection.strategy}</span>
          )}
        </div>
      </div>

      <div className={styles.summary}>
        <Markdown>{displayText}</Markdown>
      </div>

      {!expanded && reflection.summary.length > 160 && (
        <p className={styles.expandHint}>Click to expand</p>
      )}
    </div>
  );
}
