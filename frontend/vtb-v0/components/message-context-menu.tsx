"use client"

import { useEffect, useRef } from "react"
import { Reply, Edit, Trash2 } from "lucide-react"
import { useLanguage } from "@/lib/language-context"

interface MessageContextMenuProps {
  x: number
  y: number
  onReply: () => void
  onEdit: () => void
  onDelete: () => void
  onClose: () => void
  isOperatorMessage: boolean
}

export function MessageContextMenu({
  x,
  y,
  onReply,
  onEdit,
  onDelete,
  onClose,
  isOperatorMessage,
}: MessageContextMenuProps) {
  const { t } = useLanguage()
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose()
      }
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose()
      }
    }

    document.addEventListener("mousedown", handleClickOutside)
    document.addEventListener("keydown", handleEscape)

    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
      document.removeEventListener("keydown", handleEscape)
    }
  }, [onClose])

  return (
    <div
      ref={menuRef}
      className="fixed z-50 min-w-[160px] rounded-md border border-border bg-popover p-1 shadow-md"
      style={{ left: x, top: y }}
    >
      <button
        className="flex w-full items-center gap-2 rounded-sm px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
        onClick={() => {
          onReply()
          onClose()
        }}
      >
        <Reply className="h-4 w-4" />
        {t("replyToMessage")}
      </button>
      {isOperatorMessage && (
        <>
          <button
            className="flex w-full items-center gap-2 rounded-sm px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
            onClick={() => {
              onEdit()
              onClose()
            }}
          >
            <Edit className="h-4 w-4" />
            {t("editMessage")}
          </button>
          <button
            className="flex w-full items-center gap-2 rounded-sm px-3 py-2 text-sm hover:bg-destructive hover:text-destructive-foreground transition-colors"
            onClick={() => {
              onDelete()
              onClose()
            }}
          >
            <Trash2 className="h-4 w-4" />
            {t("deleteMessageAction")}
          </button>
        </>
      )}
    </div>
  )
}
