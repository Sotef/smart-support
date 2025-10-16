"use client"

import { useState } from "react"
import type { Ticket, TicketStatus } from "@/lib/types"
import { cn } from "@/lib/utils"
import { RefreshCw, Search, UserCheck } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { useLanguage } from "@/lib/language-context"

interface TicketListProps {
  tickets: Ticket[]
  onSelectTicket: (ticket: Ticket) => void
  selectedTicketId?: string
  onConnectToChat?: (ticketId: string) => void
}

export function TicketList({ tickets, onSelectTicket, selectedTicketId, onConnectToChat }: TicketListProps) {
  const { t } = useLanguage()
  const [activeTab, setActiveTab] = useState<TicketStatus>("assigned")

  const priorityRank = { HIGH: 3, MEDIUM: 2, LOW: 1 } as const
  const filteredTickets = tickets
    .filter((ticket) => ticket.status === activeTab)
    .sort((a, b) => (priorityRank[(b.priority as any) || 'MEDIUM'] - priorityRank[(a.priority as any) || 'MEDIUM']))

  const getTabCount = (status: TicketStatus) => {
    return tickets.filter((t) => t.status === status).length
  }

  const getUnreadCount = (ticket: Ticket) => {
    if (!ticket.messages) return 0
    return ticket.messages.filter(msg => 
      msg.sender !== 'operator' && 
      (!msg.readBy || !msg.readBy.includes('operator'))
    ).length
  }

  return (
    <div className="w-80 bg-card border-r border-border flex flex-col">
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-card-foreground">{t("tickets")}</h2>
          <div className="flex gap-2">
            <button className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center">
              <RefreshCw className="h-4 w-4" />
            </button>
            <button className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center">
              <Search className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab("assigned")}
            className={cn(
              "flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors relative",
              activeTab === "assigned"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {t("assigned")}
            {getTabCount("assigned") > 0 && (
              <Badge className="ml-2 bg-background/20 text-xs">{getTabCount("assigned")}</Badge>
            )}
          </button>
          <button
            onClick={() => setActiveTab("started")}
            className={cn(
              "flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors",
              activeTab === "started"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {t("started")}
            {getTabCount("started") > 0 && (
              <Badge className="ml-2 bg-background/20 text-xs">{getTabCount("started")}</Badge>
            )}
          </button>
          <button
            onClick={() => setActiveTab("solved")}
            className={cn(
              "flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors",
              activeTab === "solved"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {t("solved")}
            {getTabCount("solved") > 0 && (
              <Badge className="ml-2 bg-background/20 text-xs">{getTabCount("solved")}</Badge>
            )}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="p-2">
          <div className="text-xs font-medium text-muted-foreground px-3 py-2">Today</div>
          {filteredTickets.map((ticket) => (
            <button
              key={ticket.id}
              onClick={() => onSelectTicket(ticket)}
              className={cn(
                "w-full p-3 rounded-lg text-left transition-colors mb-1",
                selectedTicketId === ticket.id ? "bg-accent text-accent-foreground" : "hover:bg-muted",
              )}
            >
              <div className="flex items-start gap-2">
                <div
                  className={cn(
                    "w-2 h-2 rounded-full mt-2 flex-shrink-0",
                    ticket.status === "assigned"
                      ? "bg-warning"
                      : ticket.status === "started"
                        ? "bg-primary"
                        : "bg-success",
                  )}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <div className="font-medium text-sm text-card-foreground truncate">{ticket.subject}</div>
                    {ticket.status === "assigned" && onConnectToChat && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onConnectToChat(ticket.id);
                        }}
                        className="ml-2 p-1 rounded-md hover:bg-primary/10 text-primary transition-colors"
                        title="Подключиться к чату"
                      >
                        <UserCheck className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground truncate mt-1">{ticket.preview}</div>
                  <div className="flex items-center justify-between mt-2">
                    <div className="flex gap-1 flex-wrap">
                      {ticket.categoryDisplay && (
                        <Badge variant="secondary" className="text-xs font-medium">
                          {ticket.categoryDisplay}
                        </Badge>
                      )}
                      {ticket.subcategoryDisplay && (
                        <Badge variant="outline" className="text-xs border-blue-300 text-blue-700">
                          {ticket.subcategoryDisplay}
                        </Badge>
                      )}
                      {ticket.sentiment && (
                        <Badge 
                          variant="outline" 
                          className={cn(
                            "text-xs",
                            ticket.sentiment === 'positive' && "border-green-500 text-green-700",
                            ticket.sentiment === 'negative' && "border-red-500 text-red-700",
                            ticket.sentiment === 'neutral' && "border-gray-500 text-gray-700"
                          )}
                        >
                          {ticket.sentiment}
                        </Badge>
                      )}
                      {ticket.keywords && ticket.keywords.length > 0 && (
                        <Badge variant="outline" className="text-xs border-purple-300 text-purple-700">
                          {ticket.keywords[0]}
                          {ticket.keywords.length > 1 && ` +${ticket.keywords.length - 1}`}
                        </Badge>
                      )}
                    </div>
                    {/* Индикатор новых сообщений */}
                    {getUnreadCount(ticket) > 0 && selectedTicketId !== ticket.id && (
                      <div className="bg-red-500 text-white text-xs font-bold px-2 py-1 rounded-full min-w-[20px] text-center">
                        {getUnreadCount(ticket)}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
