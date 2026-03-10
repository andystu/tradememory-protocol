import type { OWMScorePoint } from '../../api/types';
import OWMScoreTrendWeb from './OWMScoreTrend.web';

export interface OWMScoreTrendProps {
  data: OWMScorePoint[];
}

export default function OWMScoreTrend({ data }: OWMScoreTrendProps) {
  return <OWMScoreTrendWeb data={data} />;
}
