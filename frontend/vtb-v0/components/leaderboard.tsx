"use client"

import type { Operator } from "@/lib/types"
import { Trophy, ChevronRight, ChevronLeft } from "lucide-react"
import { cn } from "@/lib/utils"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import { useLanguage } from "@/lib/language-context"

interface LeaderboardProps {
  operators: Operator[]
  isCollapsed?: boolean
  onToggleCollapse?: () => void
}

export function Leaderboard({ operators, isCollapsed = false, onToggleCollapse }: LeaderboardProps) {
  const { t } = useLanguage()

  return (
    <div className={cn("bg-card border-l border-border transition-all duration-300", isCollapsed ? "w-12" : "w-80")}>
      <div className="p-2 border-b border-border flex justify-center">
        <Button variant="ghost" size="icon" onClick={onToggleCollapse} className="h-8 w-8">
          {isCollapsed ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </Button>
      </div>

      {!isCollapsed && (
        <div className="p-6">
          <div className="flex items-center gap-2 mb-6">
            <Trophy className="h-5 w-5 text-warning" />
            <h2 className="text-lg font-semibold text-card-foreground">{t("leaderboard").toUpperCase()}</h2>
            <span className="text-xs text-muted-foreground ml-auto">{t("thisWeek")}</span>
          </div>

          <div className="mb-6 p-4 rounded-xl bg-primary text-primary-foreground">
            <div className="text-sm mb-1">{t("yourPosition")}</div>
            <div className="flex items-center justify-between">
              <div className="text-3xl font-bold">#25</div>
              <div className="w-3 h-3 rounded-full bg-success" />
            </div>
          </div>

          <div className="space-y-3">
            {operators.map((operator) => (
              <div
                key={operator.id}
                className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted transition-colors"
              >
                <div className="relative">
                  <Image
                    src={operator.avatar || "/placeholder.svg"}
                    alt={operator.name}
                    width={40}
                    height={40}
                    className="rounded-full"
                  />
                  <div
                    className={cn(
                      "absolute -bottom-1 -right-1 w-3 h-3 rounded-full border-2 border-card",
                      operator.isOnline ? "bg-success" : "bg-muted-foreground",
                    )}
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm text-card-foreground truncate">{operator.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {operator.issuesSolved} {t("issuesSolved")}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="text-lg font-bold text-card-foreground">#{operator.rank}</div>
                  <div
                    className={cn("w-2 h-2 rounded-full", operator.isOnline ? "bg-success" : "bg-muted-foreground")}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
