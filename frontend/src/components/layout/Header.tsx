"use client";

import { useRouter, usePathname } from "next/navigation";
import { LogOut, Bell, Search, User, Menu } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const pageNames: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/positions": "Posicoes",
  "/transactions": "Transacoes",
  "/documents": "Documentos",
  "/cash-flows": "Aportes/Saques",
  "/settings": "Configuracoes",
  "/accounts": "Contas",
};

export function Header() {
  const router = useRouter();
  const pathname = usePathname();

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  };

  const currentPage = Object.entries(pageNames).find(
    ([path]) => pathname === path || pathname.startsWith(path + "/")
  );

  return (
    <header className="sticky top-0 z-40 h-16 glass-card-subtle border-x-0 border-t-0 rounded-none">
      <div className="flex h-full items-center justify-between px-6">
        {/* Left: Mobile menu + Page title */}
        <div className="flex items-center gap-4">
          {/* Mobile menu button */}
          <button className="lg:hidden p-2 rounded-xl hover:bg-white/5 transition-colors">
            <Menu className="h-5 w-5 text-foreground-muted" />
          </button>

          {/* Mobile logo */}
          <span className="lg:hidden font-display text-xl font-bold text-gradient-vermillion">
            InvestCTR
          </span>

          {/* Page title - Desktop only */}
          {currentPage && (
            <h1 className="hidden lg:block font-display text-xl font-bold text-foreground">
              {currentPage[1]}
            </h1>
          )}
        </div>

        {/* Center: Search - Desktop only */}
        <div className="hidden lg:flex flex-1 max-w-md mx-8">
          <div className="relative w-full">
            <Input
              placeholder="Buscar ativos, transacoes..."
              variant="glass"
              className="pl-10"
              leftIcon={<Search className="h-4 w-4" />}
            />
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          {/* Notifications */}
          <button className="relative p-2 rounded-xl hover:bg-white/5 transition-colors group">
            <Bell className="h-5 w-5 text-foreground-muted group-hover:text-foreground transition-colors" />
            {/* Notification dot */}
            <span className="absolute top-1.5 right-1.5 h-2 w-2 bg-vermillion rounded-full" />
          </button>

          {/* User menu */}
          <div className="flex items-center gap-3 pl-3 ml-2 border-l border-white/10">
            <div className="hidden sm:block text-right">
              <p className="text-sm font-medium text-foreground">Usuario</p>
              <p className="text-xs text-foreground-muted">Conta Premium</p>
            </div>
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-vermillion/20 border border-vermillion/30">
              <User className="h-4 w-4 text-vermillion" />
            </div>
          </div>

          {/* Sign out */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleSignOut}
            className="ml-2 text-foreground-muted hover:text-destructive"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline ml-2">Sair</span>
          </Button>
        </div>
      </div>
    </header>
  );
}
