import { useTranslation } from 'react-i18next';
import styles from './ErrorState.module.css';

interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  const { t } = useTranslation();
  return (
    <div className={styles.errorCard}>
      <div className={styles.icon}>&#9888;</div>
      <p className={styles.message}>{message}</p>
      <button className={styles.retryButton} onClick={onRetry}>
        {t('common.retry')}
      </button>
    </div>
  );
}
