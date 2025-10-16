"use client"

import { Languages } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useLanguage } from "@/lib/language-context"

export function LanguageToggle() {
  const { language, setLanguage } = useLanguage()

  const toggleLanguage = () => {
    setLanguage(language === "en" ? "ru" : "en")
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleLanguage}
      title={language === "en" ? "Switch to Russian" : "Переключить на английский"}
    >
      <Languages className="h-5 w-5" />
      <span className="ml-1 text-xs font-semibold">{language.toUpperCase()}</span>
    </Button>
  )
}
