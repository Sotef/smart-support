"use client"

import { LayoutGrid, ClipboardList, Bell, MessageSquare, Target, User } from "lucide-react"
import { cn } from "@/lib/utils"

interface OperatorSidebarProps {
  activeView?: string
}

export function OperatorSidebar({ activeView = "tickets" }: OperatorSidebarProps) {
  const navItems = [
    { icon: LayoutGrid, label: "Dashboard", id: "dashboard" },
    { icon: ClipboardList, label: "Tickets", id: "tickets" },
    { icon: Bell, label: "Notifications", id: "notifications" },
    { icon: MessageSquare, label: "Messages", id: "messages" },
    { icon: Target, label: "Analytics", id: "analytics" },
  ]

  return (
    <div className="w-16 bg-sidebar border-r border-sidebar-border flex flex-col items-center py-4 gap-4">
      <div className="w-10 h-10 rounded-lg bg-sidebar-primary flex items-center justify-center text-sidebar-primary-foreground font-bold text-lg">
        V
      </div>

      <div className="flex-1 flex flex-col gap-2 w-full items-center">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={cn(
              "w-10 h-10 rounded-lg flex items-center justify-center transition-colors",
              activeView === item.id
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent/50",
            )}
          >
            <item.icon className="h-5 w-5" />
          </button>
        ))}
      </div>

      <button className="w-10 h-10 rounded-full bg-sidebar-accent flex items-center justify-center">
        <User className="h-5 w-5 text-sidebar-accent-foreground" />
      </button>
    </div>
  )
}
