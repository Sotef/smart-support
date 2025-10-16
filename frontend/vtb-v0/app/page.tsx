"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { UserCircle, Headphones } from "lucide-react"
import { ThemeToggle } from "@/components/theme-toggle"
import { LanguageToggle } from "@/components/language-toggle"
import { useLanguage } from "@/lib/language-context"

export default function HomePage() {
  const { t } = useLanguage()

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="absolute top-4 right-4 flex gap-2">
        <LanguageToggle />
        <ThemeToggle />
      </div>

      <div className="text-center space-y-8 p-8">
        <div className="space-y-4">
          <div className="flex items-center justify-center mb-6">
            <div className="w-16 h-16 rounded-xl bg-primary flex items-center justify-center text-primary-foreground font-bold text-2xl">
              V
            </div>
          </div>
          <h1 className="text-4xl font-bold text-foreground">{t("vtbSupportSystem")}</h1>
          <p className="text-lg text-muted-foreground">{t("systemDescription")}</p>
        </div>

        <div className="flex gap-4 justify-center">
          <Link href="/login/operator">
            <Button size="lg" className="gap-2">
              <Headphones className="h-5 w-5" />
              {t("operatorLogin")}
            </Button>
          </Link>
          <Link href="/login/client">
            <Button size="lg" variant="outline" className="gap-2 bg-transparent">
              <UserCircle className="h-5 w-5" />
              {t("clientLogin")}
            </Button>
          </Link>
        </div>

        <div className="pt-8 space-y-2 text-sm text-muted-foreground">
          <p>{t("demoAccess")}</p>
          <div className="flex gap-4 justify-center">
            <Link href="/operator">
              <Button variant="ghost" size="sm">
                {t("operatorDemo")}
              </Button>
            </Link>
            <Link href="/client">
              <Button variant="ghost" size="sm">
                {t("clientDemo")}
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
