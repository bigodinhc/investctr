"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { TrendingUp, Mail, Lock, User, ArrowRight, Check } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("As senhas não coincidem");
      return;
    }

    if (password.length < 6) {
      setError("A senha deve ter pelo menos 6 caracteres");
      return;
    }

    setLoading(true);

    const supabase = createClient();

    const { error } = await supabase.auth.signUp({
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

  const passwordStrength = () => {
    if (password.length === 0) return null;
    if (password.length < 6) return { level: 1, text: "Fraca", color: "bg-destructive" };
    if (password.length < 10) return { level: 2, text: "Média", color: "bg-warning" };
    return { level: 3, text: "Forte", color: "bg-success" };
  };

  const strength = passwordStrength();

  return (
    <div className="min-h-screen flex bg-background-deep">
      {/* Left Side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(212,168,83,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(212,168,83,0.03)_1px,transparent_1px)] bg-[size:60px_60px]" />

        {/* Gradient Overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-background-deep via-background to-background-elevated" />

        {/* Glow Effects */}
        <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-gold/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/3 left-1/4 w-64 h-64 bg-success/5 rounded-full blur-3xl" />

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
            COMECE A
            <br />
            <span className="text-gradient-gold">INVESTIR</span>
            <br />
            MELHOR HOJE
          </h1>

          <p className="text-foreground-muted text-lg max-w-md mb-12">
            Junte-se a investidores que já consolidam seus portfólios e tomam
            decisões mais inteligentes.
          </p>

          {/* Benefits */}
          <div className="space-y-4">
            {[
              "Crie sua conta em menos de 1 minuto",
              "Sem cartão de crédito necessário",
              "Acesso gratuito às funcionalidades básicas",
            ].map((benefit, i) => (
              <div
                key={i}
                className="flex items-center gap-3 text-foreground-muted"
              >
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-success/10">
                  <Check className="h-3 w-3 text-success" />
                </div>
                <span>{benefit}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right Side - Register Form */}
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
              <h2 className="font-display text-3xl tracking-wide">CRIAR CONTA</h2>
              <p className="text-foreground-muted text-sm mt-2">
                Comece a gerenciar seus investimentos
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
                  <label
                    htmlFor="password"
                    className="block text-sm font-medium text-foreground-muted"
                  >
                    Senha
                  </label>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    leftIcon={<Lock className="h-4 w-4" />}
                  />
                  {/* Password strength indicator */}
                  {strength && (
                    <div className="flex items-center gap-2 mt-2">
                      <div className="flex-1 flex gap-1">
                        {[1, 2, 3].map((level) => (
                          <div
                            key={level}
                            className={`h-1 flex-1 rounded-full transition-colors ${
                              level <= strength.level
                                ? strength.color
                                : "bg-border"
                            }`}
                          />
                        ))}
                      </div>
                      <span
                        className={`text-xs ${
                          strength.level === 1
                            ? "text-destructive"
                            : strength.level === 2
                            ? "text-warning"
                            : "text-success"
                        }`}
                      >
                        {strength.text}
                      </span>
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <label
                    htmlFor="confirmPassword"
                    className="block text-sm font-medium text-foreground-muted"
                  >
                    Confirmar Senha
                  </label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    error={
                      confirmPassword.length > 0 && password !== confirmPassword
                    }
                    leftIcon={<Lock className="h-4 w-4" />}
                  />
                  {confirmPassword.length > 0 && password !== confirmPassword && (
                    <p className="text-xs text-destructive mt-1">
                      As senhas não coincidem
                    </p>
                  )}
                </div>

                <Button
                  type="submit"
                  isLoading={loading}
                  className="w-full h-11 text-base font-semibold"
                >
                  {!loading && (
                    <>
                      Criar Conta
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </>
                  )}
                </Button>
              </form>

              <div className="mt-8 pt-6 border-t border-border text-center">
                <p className="text-sm text-foreground-muted">
                  Já tem uma conta?{" "}
                  <Link
                    href="/auth/login"
                    className="text-gold hover:text-gold-light font-medium transition-colors"
                  >
                    Entrar
                  </Link>
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Footer */}
          <p className="text-center text-xs text-foreground-dim mt-8">
            Ao criar sua conta, você concorda com nossos{" "}
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
