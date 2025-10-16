"use client"

import type React from "react"

import { useEffect, useRef, useState } from "react"
import type { Ticket, Message } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Phone, Mail, Send, Mic, Smile, Paperclip, Eye, X, UserCheck, ChevronDown, Tag, Hash, BarChart3, TrendingUp, MessageCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { useLanguage } from "@/lib/language-context"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { MessageContextMenu } from "@/components/message-context-menu"
import { Badge } from "@/components/ui/badge"

interface ChatAreaProps {
  ticket: Ticket | null
  onCloseTicket: () => void
  onResolveTicket: (resolved: boolean) => void
  onSendMessage?: (message: string, replyToId?: string) => void
  onDeleteMessage?: (messageId: string) => void
  onEditMessage?: (messageId: string, newText: string) => void
  isOperator?: boolean
  suggestedResponses?: string[]
}

export function ChatArea({
  ticket,
  onCloseTicket,
  onResolveTicket,
  onSendMessage,
  onDeleteMessage,
  onEditMessage,
  isOperator = true,
  suggestedResponses = [],
}: ChatAreaProps) {
  const { t } = useLanguage()
  const [message, setMessage] = useState("")
  const [isLogsOpen, setIsLogsOpen] = useState(false)
  const [contextMenu, setContextMenu] = useState<{
    x: number
    y: number
    messageId: string
    isOperatorMessage: boolean
  } | null>(null)
  const [replyingTo, setReplyingTo] = useState<Message | null>(null)
  const [editingMessage, setEditingMessage] = useState<{ id: string; text: string } | null>(null)
  const [suggestionsExpanded, setSuggestionsExpanded] = useState(true)
  const [analysisExpanded, setAnalysisExpanded] = useState(false)

  // Auto-scroll to bottom logic
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const bottomRef = useRef<HTMLDivElement | null>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  const scrollToBottom = (behavior: ScrollBehavior = 'auto') => {
    bottomRef.current?.scrollIntoView({ behavior })
  }

  // Re-attach autoscroll when ticket changes
  useEffect(() => {
    setAutoScroll(true)
    // wait for render
    const id = requestAnimationFrame(() => scrollToBottom('auto'))
    return () => cancelAnimationFrame(id)
  }, [ticket?.id])

  // Scroll when new messages arrive if autoscroll is enabled
  useEffect(() => {
    if (autoScroll) scrollToBottom('auto')
  }, [ticket?.messages?.length])

  if (!ticket) {
    return (
      <div className="flex-1 flex items-center justify-center bg-background">
        <div className="text-center text-muted-foreground">
          <MessageSquare className="h-16 w-16 mx-auto mb-4 opacity-20" />
          <p className="text-lg">{t("selectTicket")}</p>
        </div>
      </div>
    )
  }

  const handleSend = () => {
    if (message.trim()) {
      onSendMessage?.(message, replyingTo?.id)
      setMessage("")
      setReplyingTo(null)
    }
  }

  const handleContextMenu = (e: React.MouseEvent, msg: Message) => {
    e.preventDefault()
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      messageId: msg.id,
      isOperatorMessage: msg.sender === "operator" && isOperator,
    })
  }

  const handleReply = (messageId: string) => {
    const msg = ticket.messages.find((m) => m.id === messageId)
    if (msg) {
      setReplyingTo(msg)
    }
  }

  const handleEdit = (messageId: string) => {
    const msg = ticket.messages.find((m) => m.id === messageId)
    if (msg) {
      setEditingMessage({ id: msg.id, text: msg.text })
    }
  }

  const handleSaveEdit = () => {
    if (editingMessage && editingMessage.text.trim()) {
      onEditMessage?.(editingMessage.id, editingMessage.text)
      setEditingMessage(null)
    }
  }

  const handleDeleteMessage = (messageId: string) => {
    onDeleteMessage?.(messageId)
  }

  const visibleMessages = ticket.messages.filter((msg) => !msg.deleted)
  const deletedMessages = ticket.messages.filter((msg) => msg.deleted)

  return (
    <div className="flex-1 flex flex-col bg-background">
      {/* Header */}
      <div className="border-b border-border p-4 bg-card">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-card-foreground">{ticket.clientName}</h3>
                <span className="text-xs text-muted-foreground">• {ticket.clientEmail}</span>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                {ticket.subject} <span className="text-xs">({ticket.id})</span>
              </p>
              
              {/* Индикатор статуса подключения оператора */}
              <div className="flex items-center gap-2 mt-2">
                {ticket.status === 'started' && (
                  <div className="flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full">
                    <UserCheck className="h-3 w-3" />
                    <span>{isOperator ? 'Вы подключены к чату' : 'Оператор подключился'}</span>
                  </div>
                )}
                {ticket.status === 'assigned' && !isOperator && (
                  <div className="flex items-center gap-1 text-xs text-yellow-600 bg-yellow-50 px-2 py-1 rounded-full">
                    <div className="h-2 w-2 bg-yellow-400 rounded-full animate-pulse" />
                    <span>Ожидание оператора</span>
                  </div>
                )}
              </div>
              
              {/* Отображаем категории для оператора */}
              {isOperator && (
                <div className="mt-2">
                  {/* Всегда показываем блок категорий для оператора */}
                  <div className="flex flex-wrap gap-2 items-center">
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Tag className="h-3 w-3" />
                      <span>Категория:</span>
                    </div>
                    {ticket.categoryDisplay ? (
                      <Badge variant="secondary" className="text-xs flex items-center gap-1">
                        <Hash className="h-3 w-3" />
                        {ticket.categoryDisplay}
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-xs text-muted-foreground">
                        Не определена
                      </Badge>
                    )}
                    
                    {ticket.subcategoryDisplay && (
                      <>
                        <span className="text-xs text-muted-foreground">→</span>
                        <Badge variant="outline" className="text-xs border-blue-300 text-blue-700 flex items-center gap-1">
                          <Hash className="h-3 w-3" />
                          {ticket.subcategoryDisplay}
                        </Badge>
                      </>
                    )}
                    
                    {/* Показываем confidence score если есть */}
                    {ticket.categoryConfidence && (
                      <div className="text-xs text-muted-foreground ml-2">
                        <span className="opacity-70">({Math.round(ticket.categoryConfidence * 100)}% уверенность)</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isOperator && (
              <>
                <Button variant="ghost" size="icon">
                  <Phone className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon">
                  <Mail className="h-4 w-4" />
                </Button>
                <Dialog open={isLogsOpen} onOpenChange={setIsLogsOpen}>
                  <DialogTrigger asChild>
                    <Button variant="ghost" size="icon" title={t("viewLogs")}>
                      <Eye className="h-4 w-4" />
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                    <DialogHeader>
                      <DialogTitle>{t("deletedMessages")}</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3 py-4">
                      {deletedMessages.length === 0 ? (
                        <p className="text-center text-muted-foreground py-8">{t("noDeletedMessages")}</p>
                      ) : (
                        deletedMessages.map((msg) => (
                          <div key={msg.id} className="p-4 rounded-lg bg-muted border border-border">
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex-1">
                                <p className="text-sm">{msg.text}</p>
                                <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                                  <span>
                                    {msg.timestamp.toLocaleTimeString("ru-RU", {
                                      hour: "2-digit",
                                      minute: "2-digit",
                                    })}
                                  </span>
                                  {msg.deletedAt && (
                                    <span>
                                      {t("deletedAt")}:{" "}
                                      {msg.deletedAt.toLocaleTimeString("ru-RU", {
                                        hour: "2-digit",
                                        minute: "2-digit",
                                      })}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </DialogContent>
                </Dialog>
              </>
            )}
            <Button variant="default" onClick={onCloseTicket}>
              {t("closeTicket")}
            </Button>
          </div>
        </div>
      </div>

      {/* Панель анализа сообщений для оператора */}
      {isOperator && (
        <div className="border-b border-border bg-muted/30">
          <button
            onClick={() => setAnalysisExpanded(!analysisExpanded)}
            className="w-full p-3 flex items-center justify-between text-left hover:bg-muted/50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium text-muted-foreground">
                Анализ сообщений клиента
              </span>
              <span className="text-xs text-muted-foreground">
                ({visibleMessages.filter(m => m.sender === 'client' && (m.categoryDisplay || m.category)).length} проанализировано)
              </span>
            </div>
            <ChevronDown 
              className={cn(
                "h-4 w-4 text-muted-foreground transition-transform",
                analysisExpanded ? "rotate-180" : ""
              )}
            />
          </button>
          {analysisExpanded && (
            <div className="px-4 pb-4">
              <div className="space-y-3 max-h-60 overflow-y-auto">
                {visibleMessages
                  .filter(msg => msg.sender === 'client')
                  .map((msg, index) => (
                    <div key={msg.id} className="bg-card border border-border rounded-lg p-3">
                      <div className="flex items-start gap-3">
                        <div className="flex-shrink-0">
                          <div className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-medium">
                            {index + 1}
                          </div>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-muted-foreground mb-2 truncate">
                            «{msg.text.length > 60 ? msg.text.slice(0, 60) + '...' : msg.text}»
                          </div>
                          
                          {/* Категории */}
                          <div className="flex flex-wrap gap-1.5 items-center mb-2">
                            {msg.categoryDisplay || msg.category ? (
                              <>
                                <Badge variant="secondary" className="text-xs flex items-center gap-1">
                                  <Tag className="h-3 w-3" />
                                  {msg.categoryDisplay || msg.category}
                                </Badge>
                                {(msg.subcategoryDisplay || msg.subcategory) && (
                                  <>
                                    <span className="text-xs text-muted-foreground">→</span>
                                    <Badge variant="outline" className="text-xs border-blue-300 text-blue-700">
                                      {msg.subcategoryDisplay || msg.subcategory}
                                    </Badge>
                                  </>
                                )}
                                {msg.categoryConfidence && (
                                  <span className="text-xs text-muted-foreground">
                                    {Math.round(msg.categoryConfidence * 100)}%
                                  </span>
                                )}
                              </>
                            ) : (
                              <Badge variant="outline" className="text-xs text-muted-foreground">
                                <MessageCircle className="h-3 w-3 mr-1" />
                                Не категоризировано
                              </Badge>
                            )}
                          </div>
                          
                          {/* Тональность и ключевые слова */}
                          <div className="flex flex-wrap gap-1.5 items-center">
                            {msg.sentiment && (
                              <Badge 
                                variant="outline" 
                                className={cn(
                                  "text-xs",
                                  msg.sentiment === 'positive' && "border-green-300 text-green-700",
                                  msg.sentiment === 'negative' && "border-red-300 text-red-700",
                                  msg.sentiment === 'neutral' && "border-gray-300 text-gray-700"
                                )}
                              >
                                <TrendingUp className="h-3 w-3 mr-1" />
                                {msg.sentiment === 'positive' ? 'Позитивный' : 
                                 msg.sentiment === 'negative' ? 'Негативный' : 
                                 'Нейтральный'}
                              </Badge>
                            )}
                            {msg.keywords && msg.keywords.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {msg.keywords.slice(0, 3).map((keyword, i) => (
                                  <span key={i} className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                                    {keyword}
                                  </span>
                                ))}
                                {msg.keywords.length > 3 && (
                                  <span className="text-xs text-muted-foreground">+{msg.keywords.length - 3}</span>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                }
                
                {visibleMessages.filter(msg => msg.sender === 'client').length === 0 && (
                  <div className="text-center py-6 text-muted-foreground">
                    <MessageCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">Нет сообщений клиента для анализа</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Messages */}
      <div
        className="flex-1 overflow-y-auto p-6"
        ref={scrollRef}
        onScroll={(e) => {
          const el = e.currentTarget
          const isAtBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 8
          setAutoScroll(isAtBottom)
        }}
      >
        <div className="max-w-3xl mx-auto space-y-4">
          <div className="text-center text-xs text-muted-foreground mb-6">
            {t("today")}{" "}
            {new Date().toLocaleTimeString("ru-RU", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </div>

          {visibleMessages.map((msg) => (
            <div key={msg.id} className={cn("flex group", msg.sender === "operator" ? "justify-end" : "justify-start")}>
              <div className="flex flex-col gap-1 max-w-[70%]">
                {msg.replyTo && (
                  <div className="text-xs text-muted-foreground px-4">
                    {t("replyingTo")}: {ticket.messages.find((m) => m.id === msg.replyTo)?.text.slice(0, 50)}...
                  </div>
                )}
                <div
                  className={cn(
                    "rounded-2xl px-4 py-3 cursor-context-menu",
                    msg.sender === "operator"
                      ? "bg-foreground text-background"
                      : msg.sender === "bot"
                      ? "bg-primary/10 text-foreground"
                      : msg.sender === "system"
                      ? "bg-yellow-50 dark:bg-yellow-900/20 text-foreground border border-yellow-200 dark:border-yellow-800"
                      : "bg-muted text-foreground",
                  )}
                  onContextMenu={(e) => handleContextMenu(e, msg)}
                >
                  <p className="text-sm leading-relaxed">{msg.text}</p>
                  <div
                    className={cn(
                      "text-xs mt-1 flex items-center gap-2",
                      msg.sender === "operator" ? "text-background/70" : "text-muted-foreground",
                    )}
                  >
                    <span>
                      {msg.timestamp.toLocaleTimeString("ru-RU", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    {/* sent/read ticks for own messages */}
                    {((isOperator && msg.sender === 'operator') || (!isOperator && msg.sender === 'client')) && (
                      <span className="flex items-center gap-1">
                        {/* one tick: sent */}
                        <span title="Отправлено">✓</span>
                        {/* two ticks: read (by bot or operator/client accordingly) */}
                        {(() => {
                          const readBy = msg.readBy || []
                          // if operator is present (there is any operator message in ticket), require operator read; else allow bot read
                          const operatorPresent = ticket.messages.some(m => m.sender === 'operator')
                          const read = isOperator
                            ? readBy.includes('client')
                            : (operatorPresent ? readBy.includes('operator') : readBy.includes('bot'))
                          return read ? <span title="Прочитано">✓</span> : null
                        })()}
                      </span>
                    )}
                    {msg.editHistory && msg.editHistory.length > 0 && (
                      <span className="italic">({t("editedMessage")})</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}

          {/* Bottom sentinel for autoscroll */}
          <div ref={bottomRef} />
        </div>
      </div>

      {contextMenu && (
        <MessageContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          isOperatorMessage={contextMenu.isOperatorMessage}
          onReply={() => handleReply(contextMenu.messageId)}
          onEdit={() => handleEdit(contextMenu.messageId)}
          onDelete={() => handleDeleteMessage(contextMenu.messageId)}
          onClose={() => setContextMenu(null)}
        />
      )}

      {/* Input Area */}
      <div className="border-t border-border p-4 bg-card">
        <div className="max-w-3xl mx-auto">
          {isOperator && suggestedResponses.length > 0 && (
            <div className="mb-3 rounded-lg bg-primary/5 border border-primary/20">
              <button
                onClick={() => setSuggestionsExpanded(!suggestionsExpanded)}
                className="w-full p-3 flex items-center justify-between text-left hover:bg-primary/10 transition-colors"
              >
                <p className="text-xs font-medium text-muted-foreground">
                  {t("suggestedResponses") || "Рекомендованные ответы"} ({suggestedResponses.length})
                </p>
                <ChevronDown 
                  className={cn(
                    "h-4 w-4 text-muted-foreground transition-transform",
                    suggestionsExpanded ? "rotate-180" : ""
                  )}
                />
              </button>
              {suggestionsExpanded && (
                <div className="px-3 pb-3">
                  <div className="flex flex-col gap-1.5">
                    {suggestedResponses.map((s, i) => (
                      <Button
                        key={i}
                        size="sm"
                        variant="ghost"
                        className="justify-start text-left h-auto py-2 px-3 whitespace-normal"
                        onClick={() => onSendMessage?.(s)}
                      >
                        {s}
                      </Button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {!isOperator && ticket.status === "solved" && (
            <div className="mb-4 flex gap-2">
              <Button variant="default" className="flex-1" onClick={() => onResolveTicket(true)}>
                {t("issueResolved")}
              </Button>
              <Button variant="outline" className="flex-1 bg-transparent" onClick={() => onResolveTicket(false)}>
                {t("issueNotResolved")}
              </Button>
            </div>
          )}

          {replyingTo && (
            <div className="mb-2 flex items-center justify-between bg-muted px-3 py-2 rounded-lg">
              <div className="flex-1">
                <p className="text-xs text-muted-foreground">{t("replyingTo")}</p>
                <p className="text-sm truncate">{replyingTo.text}</p>
              </div>
              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setReplyingTo(null)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          )}

          {editingMessage ? (
            <div className="space-y-2">
              <Textarea
                value={editingMessage.text}
                onChange={(e) => setEditingMessage({ ...editingMessage, text: e.target.value })}
                className="min-h-[48px] max-h-32 resize-none"
              />
              <div className="flex gap-2">
                <Button onClick={handleSaveEdit} size="sm">
                  {t("saveEdit")}
                </Button>
                <Button variant="outline" onClick={() => setEditingMessage(null)} size="sm">
                  {t("cancelEdit")}
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex items-end gap-2">
              <div className="flex-1 relative">
                <Textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder={t("typeMessage")}
                  className="min-h-[48px] max-h-32 resize-none pr-24"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault()
                      handleSend()
                    }
                  }}
                />
                <div className="absolute right-2 bottom-2 flex gap-1">
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Mic className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Smile className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Paperclip className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <Button onClick={handleSend} size="icon" className="h-12 w-12 flex-shrink-0">
                <Send className="h-5 w-5" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function MessageSquare({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  )
}
