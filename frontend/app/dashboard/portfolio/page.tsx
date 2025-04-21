import { PortfolioHeader } from "@/components/dashboard/portfolio/portfolio-header"
import { PortfolioTable } from "@/components/dashboard/portfolio/portfolio-table"
import { PortfolioChartsWrapper } from "@/components/dashboard/portfolio/portfolio-charts-wrapper"

export default function PortfolioPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Portfolio</h1>
      <PortfolioHeader />
      <PortfolioChartsWrapper />
      <PortfolioTable />
    </div>
  )
}

