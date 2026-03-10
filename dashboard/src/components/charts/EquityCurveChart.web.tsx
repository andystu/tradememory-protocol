import { useEffect, useRef } from 'react';
import { createChart, ColorType, AreaSeries, type IChartApi } from 'lightweight-charts';

export interface EquityCurveWebProps {
  data: {
    time: string;
    value: number;
    drawdown: number;
    trades: number;
  }[];
}

export default function EquityCurveChartWeb({ data }: EquityCurveWebProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#6a6a80',
        fontFamily: "'JetBrains Mono', monospace",
      },
      grid: {
        vertLines: { color: 'rgba(26, 26, 40, 0.5)' },
        horzLines: { color: 'rgba(26, 26, 40, 0.5)' },
      },
      width: container.clientWidth,
      height: container.clientHeight,
      rightPriceScale: {
        borderColor: '#1a1a28',
      },
      timeScale: {
        borderColor: '#1a1a28',
      },
      crosshair: {
        horzLine: { color: '#00e5ff', style: 2 },
        vertLine: { color: '#00e5ff', style: 2 },
      },
    });

    chartRef.current = chart;

    const areaSeries = chart.addSeries(AreaSeries, {
      topColor: 'rgba(0, 229, 255, 0.3)',
      bottomColor: 'rgba(0, 229, 255, 0.02)',
      lineColor: '#00e5ff',
      lineWidth: 2,
      crosshairMarkerBackgroundColor: '#00e5ff',
    });

    areaSeries.setData(
      data.map((d) => ({
        time: d.time,
        value: d.value,
      }))
    );

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (container) {
        chart.applyOptions({ width: container.clientWidth });
      }
    };

    const observer = new ResizeObserver(handleResize);
    observer.observe(container);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [data]);

  return (
    <div
      ref={containerRef}
      style={{ width: '100%', height: '100%' }}
    />
  );
}
