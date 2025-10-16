"use client"

import React, { useState, useEffect } from "react"
import { ChatArea } from "@/components/chat-area"
import { ThemeToggle } from "@/components/theme-toggle"
import { LanguageToggle } from "@/components/language-toggle"
import { useLanguage } from "@/lib/language-context"
import type { Ticket } from "@/lib/types"
import { cn } from "@/lib/utils"
import { MessageSquare, History, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"

export default function ClientPage() {
  const { t } = useLanguage()
  const [activeTab, setActiveTab] = useState<"current" | "history">("current")
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null)

  const mapSessionToTicket = (s: any): Ticket => ({
    id: s.id,
    clientName: 'Current User',
    clientEmail: 'user@example.com',
    subject: s.subject || 'Вопрос',
    preview: (s.messages?.[0]?.text) || '',
    status: (s.status || 'assigned') as any,
    createdAt: new Date(s.created_at || Date.now()),
    messages: (s.messages || [])
      .filter((m: any) => !m.visible_to || m.visible_to === 'client' || m.visible_to === 'all')
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
      })),
  })

  const refreshSessions = async () => {
    try {
      const resp = await fetch('/api/session/list')
      if (!resp.ok) return
      const data = await resp.json()
      const items = (data.items || []).map(mapSessionToTicket)
      setTickets(items)
      if (!selectedTicket && items[0]) setSelectedTicket(items[0])
    } catch {}
  }

useEffect(() => { 
  refreshSessions()
  
  // WebSocket для real-time обновлений чата
  try {
    // Используем переменную окружения для WebSocket URL
    const wsUrl = process.env.NEXT_PUBLIC_WEBSOCKET_URL || (
      typeof window !== 'undefined' 
        ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname}:8000`
        : 'ws://localhost:8000'
    )
    const ws = new WebSocket(`${wsUrl}/ws/operator_dashboard`)
    
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        if (msg.type === 'message_created' || msg.type === 'message_read') {
          // Обновляем чат при новых сообщениях
          refreshSessions()
        } else if (msg.type === 'operator_connected') {
          // Оператор подключился к чату
          console.log('🎯 Operator connected:', msg.operator_id)
          // Обновляем сессии, чтобы показать новый статус
          refreshSessions()
          // Если это текущий выбранный тикет, показываем уведомление
          if (selectedTicket?.id === msg.session_id) {
            // Здесь можно добавить toast-уведомление или другой UI индикатор
            console.log('Оператор подключился к вашему чату!')
          }
        }
      } catch {}
    }
    
    return () => ws.close()
  } catch {}
}, [])

  // mark reads when viewing chat
  useEffect(() => {
    if (selectedTicket) {
      fetch('/api/message/read', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: selectedTicket.id, reader: 'client' }) })
    }
  }, [selectedTicket?.id, selectedTicket?.messages?.length])
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [newQuestion, setNewQuestion] = useState({ subject: "", description: "" })
  const [creating, setCreating] = useState(false)

  const handleCloseTicket = async () => {
    if (!selectedTicket) return
    try {
      await fetch('/api/session/close', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: selectedTicket.id, resolved: true }) })
      await refreshSessions()
      setSelectedTicket(null)
    } catch {}
  }

  const handleResolveTicket = async (resolved: boolean) => {
    if (!selectedTicket) return
    try {
      await fetch('/api/session/close', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: selectedTicket.id, resolved }) })
      await refreshSessions()
    } catch {}
  }

  const handleSendMessage = async (message: string) => {
    if (!selectedTicket) return
    // optimistic append
    const tempId = `temp_${Date.now()}`
    const optimisticMsg = { id: tempId, text: message, sender: 'client' as const, timestamp: new Date(), status: 'sending' as const, readBy: ['client'] as any }
    const optimisticTicket: Ticket = { ...selectedTicket, messages: [...selectedTicket.messages, optimisticMsg] }
    setSelectedTicket(optimisticTicket)
    setTickets((prev) => prev.map((t) => (t.id === optimisticTicket.id ? optimisticTicket : t)))

    try {
      const resp = await fetch('/api/message/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: selectedTicket.id, sender: 'client', text: message }),
      })
      if (resp.ok) {
        const data = await resp.json()
        const updated = mapSessionToTicket({ id: selectedTicket.id, subject: selectedTicket.subject, status: data.status, messages: data.messages })
        setSelectedTicket(updated)
        setTickets((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
        // mark bot read already handled on server; mark client reads
        fetch('/api/message/read', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: selectedTicket.id, reader: 'client' }) })
      }
    } catch {}
  }

  const handleCreateQuestion = async () => {
    if (!newQuestion.subject || !newQuestion.description) return
    setCreating(true)
    try {
      const resp = await fetch('/api/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: 'client_demo', subject: newQuestion.subject, description: newQuestion.description }),
      })
      if (!resp.ok) {
        const errorText = await resp.text().catch(() => '')
        console.error('session/start failed', resp.status, errorText)
        let errorDetail = ''
        try {
          const errorJson = JSON.parse(errorText)
          errorDetail = errorJson.detail || errorText
        } catch {
          errorDetail = errorText || `HTTP ${resp.status}`
        }
        alert(`Failed to create question: ${errorDetail}`)
        setCreating(false)
        return
      }
      const data = await resp.json()
      const t = mapSessionToTicket({ id: data.session_id, subject: data.subject, status: data.status, messages: data.messages })
      setTickets((prev) => [t, ...prev])
      setSelectedTicket(t)
      setActiveTab('current')
      setIsDialogOpen(false)
      setNewQuestion({ subject: '', description: '' })
    } catch (e) {
      console.error('session/start error', e)
      alert(`Error creating question: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      <div className="flex items-center justify-between px-6 py-4 bg-card border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold">
            V
          </div>
          <h1 className="text-xl font-semibold text-card-foreground">VTB Support</h1>
        </div>
        <div className="flex items-center gap-2">
          <LanguageToggle />
          <ThemeToggle />
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-64 bg-card border-r border-border p-4">
          <div className="space-y-2">
            <button
              onClick={() => setActiveTab("current")}
              className={cn(
                "w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-left",
                activeTab === "current"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted",
              )}
            >
              <MessageSquare className="h-5 w-5" />
              <span className="font-medium">{t("currentChat")}</span>
            </button>
            <button
              onClick={() => setActiveTab("history")}
              className={cn(
                "w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-left",
                activeTab === "history"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted",
              )}
            >
              <History className="h-5 w-5" />
              <span className="font-medium">{t("myQuestions")}</span>
            </button>
          </div>

          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button className="w-full mt-4" variant="default">
                <Plus className="h-4 w-4 mr-2" />
                {t("newQuestion")}
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{t("createQuestion")}</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="subject">{t("questionSubject")}</Label>
                  <Input
                    id="subject"
                    placeholder={t("questionSubject")}
                    value={newQuestion.subject}
                    onChange={(e) => setNewQuestion({ ...newQuestion, subject: e.target.value })}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        // В поле subject Enter переходит к description
                        document.getElementById('description')?.focus()
                      }
                    }}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">{t("questionDescription")}</Label>
                  <Textarea
                    id="description"
                    placeholder={t("questionDescription")}
                    value={newQuestion.description}
                    onChange={(e) => setNewQuestion({ ...newQuestion, description: e.target.value })}
                    className="min-h-[120px]"
                    onKeyDown={(e) => {
                      // Ctrl+Enter или Cmd+Enter отправляет форму
                      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                        e.preventDefault()
                        if (newQuestion.subject.trim() && newQuestion.description.trim() && !creating) {
                          handleCreateQuestion()
                        }
                      }
                    }}
                  />
                  <p className="text-xs text-muted-foreground">Ctrl+Enter для отправки</p>
                </div>
                <Button onClick={handleCreateQuestion} className="w-full" disabled={creating}>
                  {creating ? '...' : t("submit")}
                </Button>
              </div>
            </DialogContent>
          </Dialog>

          {activeTab === "history" && (
            <div className="mt-6 space-y-2">
              <div className="text-xs font-medium text-muted-foreground px-2 mb-2">Previous Tickets</div>
              {tickets.map((ticket) => (
                <button
                  key={ticket.id}
                  onClick={() => setSelectedTicket(ticket)}
                  className={cn(
                    "w-full p-3 rounded-lg text-left transition-colors",
                    selectedTicket?.id === ticket.id ? "bg-accent text-accent-foreground" : "hover:bg-muted",
                  )}
                >
                  <div className="font-medium text-sm truncate">{ticket.subject}</div>
                  <div className="text-xs text-muted-foreground mt-1">{ticket.createdAt.toLocaleDateString()}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        <ChatArea
          ticket={activeTab === "current" ? selectedTicket : selectedTicket}
          onCloseTicket={handleCloseTicket}
          onResolveTicket={handleResolveTicket}
          onSendMessage={handleSendMessage}
          isOperator={false}
        />
      </div>
    </div>
  )
}
