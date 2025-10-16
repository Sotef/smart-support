"use client"

import React, { useState, useEffect } from "react"
import { OperatorSidebar } from "@/components/operator-sidebar"
import { TicketList } from "@/components/ticket-list"
import { ChatArea } from "@/components/chat-area"
import { Leaderboard } from "@/components/leaderboard"
import { StatsBar } from "@/components/stats-bar"
import { ThemeToggle } from "@/components/theme-toggle"
import { LanguageToggle } from "@/components/language-toggle"
import { mockOperators } from "@/lib/mock-data"
import type { Ticket, Message } from "@/lib/types"

export default function OperatorPage() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null)
  const [isLeaderboardCollapsed, setIsLeaderboardCollapsed] = useState(false)
  const [suggested, setSuggested] = useState<string[]>([])
  const [lastRequestId, setLastRequestId] = useState<string | null>(null)
  const [analyticsData, setAnalyticsData] = useState<any>(null)

  const mapSessionToTicket = (s: any): Ticket => {
    const msgs: Message[] = (s.messages || [])
      .filter((m: any) => !m.visible_to || m.visible_to === 'operator' || m.visible_to === 'all')
      .map((m: any) => ({
        id: m.id,
        text: m.text,
        sender: m.sender,
        timestamp: new Date(m.timestamp || Date.now()),
        deleted: m.deleted,
        deletedAt: m.deletedAt ? new Date(m.deletedAt) : undefined,
        replyTo: m.replyTo,
        editHistory: m.editHistory,
        status: m.status || 'sent',
        readBy: m.read_by || [],
      }))
    
    // Находим данные аналитики для этой сессии
    const analytics = analyticsData?.sessions?.find((a: any) => a.session_id === s.id)
    
    return {
      id: s.id,
      clientName: s.client_id || 'Client',
      clientEmail: 'unknown@example.com',
      subject: s.subject || 'Вопрос',
      preview: msgs[0]?.text || '',
      status: (s.status || 'assigned') as any,
      createdAt: new Date(s.created_at || Date.now()),
      messages: msgs,
      priority: (s.priority as any) || 'MEDIUM',
      category: analytics?.category,
      categoryDisplay: analytics?.category_display,
      subcategory: analytics?.subcategory,
      subcategoryDisplay: analytics?.subcategory_display,
      sentiment: analytics?.sentiment,
      keywords: analytics?.keywords,
    }
  }

  const loadAnalytics = async () => {
    try {
      const resp = await fetch('/api/session/analytics')
      if (resp.ok) {
        const data = await resp.json()
        setAnalyticsData(data)
        return data
      }
    } catch {}
    return null
  }

  const refreshSessions = async () => {
    try {
      // Сначала загружаем аналитику, чтобы она была доступна в mapSessionToTicket
      const analytics = await loadAnalytics()
      
      const resp = await fetch('/api/session/list')
      if (!resp.ok) return
      const data = await resp.json()
      const items = (data.items || []).map(mapSessionToTicket)
      setTickets(items)
    } catch {}
  }

  // initial load + WebSocket RT обновления
  useEffect(() => {
    refreshSessions()
    // RT: подписка на события сервера
    try {
      const proto = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws'
      const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost'
      const ws = new WebSocket(`${proto}://${host}:8000/ws/operator_dashboard`)
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data)
          if (msg.type === 'session_started' || msg.type === 'message_created' || msg.type === 'analysis_complete' || msg.type === 'message_read') {
            refreshSessions()
          } else if (msg.type === 'message_categorized') {
            // Отображаем уведомление о новой категоризации
            console.log('📊 New message categorized:', {
              session: msg.session_id,
              category: msg.category,
              subcategory: msg.subcategory,
              confidence: msg.confidence,
              text: msg.text
            })
            // Обновляем список для отображения новых категорий
            refreshSessions()
          }
        } catch {}
      }
      return () => ws.close()
    } catch {}
  }, [])

  // Горячие клавиши для переключения между чатами
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + 1-9 для быстрого переключения между чатами
      if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '9') {
        e.preventDefault()
        const index = parseInt(e.key) - 1
        if (tickets[index]) {
          setSelectedTicket(tickets[index])
        }
      }
      // Ctrl/Cmd + ↑/↓ для навигации по списку чатов
      else if ((e.ctrlKey || e.metaKey) && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
        e.preventDefault()
        if (!selectedTicket || tickets.length === 0) return
        
        const currentIndex = tickets.findIndex(t => t.id === selectedTicket.id)
        if (currentIndex === -1) return
        
        let newIndex
        if (e.key === 'ArrowUp') {
          newIndex = currentIndex > 0 ? currentIndex - 1 : tickets.length - 1
        } else {
          newIndex = currentIndex < tickets.length - 1 ? currentIndex + 1 : 0
        }
        
        setSelectedTicket(tickets[newIndex])
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [tickets, selectedTicket])

  // mark reads when viewing a ticket
  useEffect(() => {
    if (selectedTicket?.id) {
      fetch('/api/message/read', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: selectedTicket.id, reader: 'operator' }) })
    }
  }, [selectedTicket?.id, selectedTicket?.messages?.length])

  const handleCloseTicket = async () => {
    if (!selectedTicket) return
    try {
      await fetch('/api/session/close', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: selectedTicket.id, resolved: true }),
      })
      await refreshSessions()
      setSelectedTicket(null)
    } catch {}
  }

  const handleResolveTicket = (resolved: boolean) => {
    console.log("[v0] Ticket resolved:", resolved)
  }

  const handleSendMessage = async (message: string, replyToId?: string) => {
    if (!selectedTicket) return
    // optimistic append
    const tempId = `temp_${Date.now()}`
    const optimistic: Message = {
      id: tempId,
      text: message,
      sender: 'operator',
      timestamp: new Date(),
      status: 'sending',
      readBy: ['operator'],
      replyTo: replyToId,
    }
    const optimisticTicket: Ticket = { ...selectedTicket, messages: [...selectedTicket.messages, optimistic] }
    setSelectedTicket(optimisticTicket)
    setTickets((prev) => prev.map((t) => (t.id === optimisticTicket.id ? optimisticTicket : t)))

    try {
      const resp = await fetch('/api/message/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: selectedTicket.id, sender: 'operator', text: message, reply_to: replyToId }),
      })
      if (resp.ok) {
        const data = await resp.json()
        const updated = mapSessionToTicket({ id: selectedTicket.id, subject: selectedTicket.subject, client_id: selectedTicket.clientName, status: data.status, messages: data.messages })
        setSelectedTicket(updated)
        setTickets((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
        setSuggested(data.suggested_responses || [])
        // mark as read by operator on arrival
        fetch('/api/message/read', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: selectedTicket.id, reader: 'operator' }) })
      }
    } catch {}
  }

  const handleDeleteMessage = async (messageId: string) => {
    if (!selectedTicket) return
    try {
      const resp = await fetch('/api/message/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: selectedTicket.id, message_id: messageId }),
      })
      if (resp.ok) {
        const data = await resp.json()
        const updated = mapSessionToTicket({ id: selectedTicket.id, subject: selectedTicket.subject, client_id: selectedTicket.clientName, status: data.status || selectedTicket.status, messages: data.messages })
        setSelectedTicket(updated)
        setTickets((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
      }
    } catch {}
  }

  const handleEditMessage = async (messageId: string, newText: string) => {
    if (!selectedTicket) return
    try {
      const resp = await fetch('/api/message/edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: selectedTicket.id, message_id: messageId, new_text: newText }),
      })
      if (resp.ok) {
        const data = await resp.json()
        const updated = mapSessionToTicket({ id: selectedTicket.id, subject: selectedTicket.subject, client_id: selectedTicket.clientName, status: data.status || selectedTicket.status, messages: data.messages })
        setSelectedTicket(updated)
        setTickets((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
      }
    } catch {}
  }

  const handleConnectToChat = async (ticketId: string) => {
    try {
      const operatorId = `op_${Date.now()}` // В реальном приложении это ID текущего оператора
      const resp = await fetch('/api/session/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          session_id: ticketId, 
          operator_id: operatorId 
        }),
      })
      
      if (resp.ok) {
        const data = await resp.json()
        console.log('Connected to chat:', data)
        
        // Обновляем список тикетов
        await refreshSessions()
        
        // Автоматически выбираем подключенный тикет
        const connectedTicket = tickets.find(t => t.id === ticketId)
        if (connectedTicket) {
          const updatedTicket = { ...connectedTicket, status: 'started' as any }
          setSelectedTicket(updatedTicket)
        }
      } else {
        console.error('Failed to connect to chat:', await resp.text())
      }
    } catch (error) {
      console.error('Error connecting to chat:', error)
    }
  }

  const stats = {
    issuesPending: 86,
    issuesEscalated: 2,
    responseTime: 60,
  }

  return (
    <div className="h-screen flex flex-col">
      <div className="flex-1 flex overflow-hidden">
        <OperatorSidebar activeView="tickets" />
        <div className="flex-1 flex flex-col">
          <div className="flex items-center justify-between px-6 py-3 bg-card border-b border-border">
            <div className="flex items-center gap-4">
              <h1 className="text-xl font-semibold text-card-foreground">Support Dashboard</h1>
              <div className="text-xs text-muted-foreground hidden md:block">
                Ctrl+1-9: Быстрое переключение • Ctrl+↑↓: Навигация
              </div>
            </div>
            <div className="flex items-center gap-2">
              <LanguageToggle />
              <ThemeToggle />
            </div>
          </div>
          <StatsBar stats={stats} />
          <div className="flex-1 flex overflow-hidden">
            <TicketList 
              tickets={tickets} 
              onSelectTicket={setSelectedTicket} 
              selectedTicketId={selectedTicket?.id}
              onConnectToChat={handleConnectToChat}
            />
            <ChatArea
              ticket={selectedTicket}
              onCloseTicket={handleCloseTicket}
              onResolveTicket={handleResolveTicket}
              onSendMessage={handleSendMessage}
              onDeleteMessage={handleDeleteMessage}
              onEditMessage={handleEditMessage}
              isOperator={true}
              suggestedResponses={suggested}
            />
            <Leaderboard
              operators={mockOperators}
              isCollapsed={isLeaderboardCollapsed}
              onToggleCollapse={() => setIsLeaderboardCollapsed(!isLeaderboardCollapsed)}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
