"use client"

import { useLanguage } from "@/lib/language-context"

interface StatsBarProps {
  stats: {
    issuesPending: number
    issuesEscalated: number
    responseTime: number
  }
}

export function StatsBar({ stats }: StatsBarProps) {
  const { t } = useLanguage()

  return (
    <div className="bg-card border-b border-border px-6 py-4">
      <div className="flex items-center gap-8">
        <div>
          <div className="text-xs text-muted-foreground mb-1">{t("issuesPending")}</div>
          <div className="text-2xl font-bold text-card-foreground">{stats.issuesPending}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground mb-1">{t("issuesEscalated")}</div>
          <div className="text-2xl font-bold text-card-foreground">{stats.issuesEscalated}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground mb-1">{t("responseTimeAvg")}</div>
          <div className="text-2xl font-bold text-card-foreground">{stats.responseTime}s</div>
        </div>
      </div>
    </div>
  )
}
