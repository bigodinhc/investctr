"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { TrendingUp, Mail, Lock, ArrowRight } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const supabase = createClient();

    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }

    router.push("/dashboard");
    router.refresh();
  };

  return (
    <div className="min-h-screen flex bg-background-deep">
      {/* Left Side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(212,168,83,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(212,168,83,0.03)_1px,transparent_1px)] bg-[size:60px_60px]" />

        {/* Gradient Overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-background-deep via-background to-background-elevated" />

        {/* Glow Effects */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-gold/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-gold/10 rounded-full blur-3xl" />

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-center px-16 py-12">
          {/* Logo */}
          <div className="flex items-center gap-4 mb-12">
            <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-gold/10 border border-gold/20">
              <TrendingUp className="h-7 w-7 text-gold" />
            </div>
            <span className="font-display text-4xl text-gradient-gold tracking-wider">
              INVESTCTR
            </span>
          </div>

          {/* Tagline */}
          <h1 className="font-display text-5xl leading-tight mb-6">
            GERENCIE SEUS
            <br />
            <span className="text-gradient-gold">INVESTIMENTOS</span>
            <br />
            COM PRECISÃO
          </h1>

          <p className="text-foreground-muted text-lg max-w-md mb-12">
            Consolide seu portfólio, acompanhe performance em tempo real e tome
            decisões baseadas em dados.
          </p>

          {/* Feature List */}
          <div className="space-y-4">
            {[
              "Visão unificada de múltiplas corretoras",
              "Métricas de risco profissionais",
              "Importação automática via PDF",
            ].map((feature, i) => (
              <div
                key={i}
                className="flex items-center gap-3 text-foreground-muted"
              >
                <div className="h-1.5 w-1.5 rounded-full bg-gold" />
                <span>{feature}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-10">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gold/10 border border-gold/20">
              <TrendingUp className="h-6 w-6 text-gold" />
            </div>
            <span className="font-display text-3xl text-gradient-gold tracking-wider">
              INVESTCTR
            </span>
          </div>

          <Card variant="elevated" className="animate-fade-in">
            <CardHeader className="text-center pb-2">
              <h2 className="font-display text-3xl tracking-wide">ENTRAR</h2>
              <p className="text-foreground-muted text-sm mt-2">
                Acesse sua conta para continuar
              </p>
            </CardHeader>

            <CardContent className="pt-6">
              <form onSubmit={handleSubmit} className="space-y-5">
                {error && (
                  <div className="p-3 bg-destructive/10 border border-destructive/20 text-destructive text-sm rounded-lg animate-fade-in">
                    {error}
                  </div>
                )}

                <div className="space-y-2">
                  <label
                    htmlFor="email"
                    className="block text-sm font-medium text-foreground-muted"
                  >
                    Email
                  </label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="seu@email.com"
                    required
                    leftIcon={<Mail className="h-4 w-4" />}
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label
                      htmlFor="password"
                      className="block text-sm font-medium text-foreground-muted"
                    >
                      Senha
                    </label>
                    <Link
                      href="/auth/forgot-password"
                      className="text-xs text-gold hover:text-gold-light transition-colors"
                    >
                      Esqueceu a senha?
                    </Link>
                  </div>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    leftIcon={<Lock className="h-4 w-4" />}
                  />
                </div>

                <Button
                  type="submit"
                  isLoading={loading}
                  className="w-full h-11 text-base font-semibold"
                >
                  {!loading && (
                    <>
                      Entrar
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </>
                  )}
                </Button>
              </form>

              <div className="mt-8 pt-6 border-t border-border text-center">
                <p className="text-sm text-foreground-muted">
                  Não tem conta?{" "}
                  <Link
                    href="/auth/register"
                    className="text-gold hover:text-gold-light font-medium transition-colors"
                  >
                    Criar conta
                  </Link>
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Footer */}
          <p className="text-center text-xs text-foreground-dim mt-8">
            Ao entrar, você concorda com nossos{" "}
            <Link href="/terms" className="text-foreground-muted hover:text-gold">
              Termos de Uso
            </Link>{" "}
            e{" "}
            <Link href="/privacy" className="text-foreground-muted hover:text-gold">
              Política de Privacidade
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
