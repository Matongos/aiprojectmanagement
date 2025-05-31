"use client";

import { useEffect, useRef } from 'react';
import { Chart, ChartConfiguration, ChartOptions } from 'chart.js/auto';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ProjectMetricsChartProps {
  data: {
    labels: string[];
    datasets: {
      label: string;
      data: number[];
      backgroundColor?: string[];
      borderColor?: string;
      fill?: boolean;
    }[];
  };
  title: string;
  type: 'line' | 'bar' | 'pie' | 'doughnut';
  height?: number;
  options?: ChartOptions;
}

export function ProjectMetricsChart({ 
  data, 
  title, 
  type, 
  height = 300,
  options: customOptions 
}: ProjectMetricsChartProps) {
  const chartRef = useRef<HTMLCanvasElement>(null);
  const chartInstance = useRef<Chart | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // Destroy existing chart
    if (chartInstance.current) {
      chartInstance.current.destroy();
    }

    const ctx = chartRef.current.getContext('2d');
    if (!ctx) return;

    const defaultOptions: ChartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top' as const,
        },
        title: {
          display: false,
        },
      },
      scales: type !== 'pie' && type !== 'doughnut' ? {
        y: {
          beginAtZero: true,
        },
      } : undefined,
    };

    const config: ChartConfiguration = {
      type,
      data,
      options: customOptions || defaultOptions,
    };

    chartInstance.current = new Chart(ctx, config);

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
      }
    };
  }, [data, type, customOptions]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div style={{ height: `${height}px` }}>
          <canvas ref={chartRef} />
        </div>
      </CardContent>
    </Card>
  );
} 