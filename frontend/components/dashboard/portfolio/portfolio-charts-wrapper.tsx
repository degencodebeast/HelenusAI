'use client';

import dynamic from 'next/dynamic';

// Dynamically import the actual charts component with ssr: false
const PortfolioCharts = dynamic(
  () => import('./portfolio-charts').then((mod) => mod.PortfolioCharts),
  { ssr: false }
);

// This wrapper component simply renders the dynamically imported charts
export function PortfolioChartsWrapper() {
  return <PortfolioCharts />;
} 