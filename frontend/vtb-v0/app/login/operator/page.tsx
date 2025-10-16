"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ThemeToggle } from "@/components/theme-toggle"
import { LanguageToggle } from "@/components/language-toggle"
import { useLanguage } from "@/lib/language-context"
import Link from "next/link"

export default function OperatorLoginPage() {
  const { t } = useLanguage()
  const [isLogin, setIsLogin] = useState(true)
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    name: "",
    corporateCode: "",
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (isLogin) {
        const params = new URLSearchParams()
        params.set('username', formData.email)
        params.set('password', formData.password)
        const resp = await fetch('/auth/login', { method: 'POST', body: params })
        if (resp.ok) {
          location.href = '/operator'
        }
      } else {
        const resp = await fetch('/auth/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: formData.email, password: formData.password, role: 'operator', name: formData.name, corporate_code: formData.corporateCode }) })
        if (resp.ok) {
          location.href = '/operator'
        } else {
          // если код/почта заняты — переключаем на вход
          setIsLogin(true)
        }
      }
    } catch {
      setIsLogin(true)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="absolute top-4 right-4 flex gap-2">
        <LanguageToggle />
        <ThemeToggle />
      </div>

      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <div className="flex items-center justify-center mb-4">
            <div className="w-12 h-12 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold text-xl">
              V
            </div>
          </div>
          <CardTitle className="text-2xl text-center">
            {isLogin ? t("operatorLogin") : t("operatorRegistration")}
          </CardTitle>
          <CardDescription className="text-center">
            {isLogin ? t("enterOperatorCredentials") : t("createOperatorAccount")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="name">{t("fullName")}</Label>
                  <Input
                    id="name"
                    placeholder="John Doe"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="corporateCode">Корп. код (VTB******)</Label>
                  <Input
                    id="corporateCode"
                    placeholder="VTB123456"
                    value={formData.corporateCode}
                    onChange={(e) => setFormData({ ...formData, corporateCode: e.target.value })}
                    required
                  />
                </div>
              </>
            )}

            <div className="space-y-2">
              <Label htmlFor="email">{t("email")}</Label>
              <Input
                id="email"
                type="email"
                placeholder="operator@vtb.com"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">{t("password")}</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
              />
            </div>

            <Button type="submit" className="w-full">
              {isLogin ? t("signIn") : t("createAccount")}
            </Button>

            <div className="text-center text-sm">
              <button type="button" onClick={() => setIsLogin(!isLogin)} className="text-primary hover:underline">
                {isLogin ? t("dontHaveAccount") + " " + t("register") : t("alreadyHaveAccount") + " " + t("signIn")}
              </button>
            </div>

            <div className="text-center text-sm text-muted-foreground">
              <Link href="/login/client" className="hover:text-foreground">
                {t("switchToClient")}
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
