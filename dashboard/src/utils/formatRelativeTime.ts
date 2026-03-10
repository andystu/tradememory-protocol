/**
 * Format a Date as relative time string.
 * "Updated just now" / "Updated 2 min ago" / exact time if >1hr.
 */
export function formatRelativeTime(date: Date): string {
  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);

  if (diffMin < 1) return 'Updated just now';
  if (diffMin < 60) return `Updated ${diffMin} min ago`;

  return `Updated ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
}
