"use client";

import { useRouter, usePathname } from "next/navigation";
import { LogOut, Bell, Search, User, Menu } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const pageNames: Record<string, string> = {
  "/dashboard": "DASHBOARD",
  "/positions": "POSIÇÕES",
  "/transactions": "TRANSAÇÕES",
  "/documents": "DOCUMENTOS",
  "/cash-flows": "APORTES/SAQUES",
  "/settings": "CONFIGURAÇÕES",
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
    <header className="sticky top-0 z-40 h-16 border-b border-border glass">
      <div className="flex h-full items-center justify-between px-6">
        {/* Left: Mobile menu + Page title */}
        <div className="flex items-center gap-4">
          {/* Mobile menu button */}
          <button className="lg:hidden p-2 rounded-md hover:bg-background-surface transition-colors">
            <Menu className="h-5 w-5 text-foreground-muted" />
          </button>

          {/* Mobile logo */}
          <span className="lg:hidden font-display text-xl text-gradient-gold tracking-wider">
            INVESTCTR
          </span>

          {/* Page title - Desktop only */}
          {currentPage && (
            <h1 className="hidden lg:block font-display text-2xl tracking-wider text-foreground">
              {currentPage[1]}
            </h1>
          )}
        </div>

        {/* Center: Search - Desktop only */}
        <div className="hidden lg:flex flex-1 max-w-md mx-8">
          <div className="relative w-full">
            <Input
              placeholder="Buscar ativos, transações..."
              className="pl-10 bg-background-surface border-transparent focus-visible:bg-background"
              leftIcon={<Search className="h-4 w-4" />}
            />
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          {/* Notifications */}
          <button className="relative p-2 rounded-md hover:bg-background-surface transition-colors group">
            <Bell className="h-5 w-5 text-foreground-muted group-hover:text-foreground transition-colors" />
            {/* Notification dot */}
            <span className="absolute top-1.5 right-1.5 h-2 w-2 bg-gold rounded-full" />
          </button>

          {/* User menu */}
          <div className="flex items-center gap-3 pl-3 ml-2 border-l border-border">
            <div className="hidden sm:block text-right">
              <p className="text-sm font-medium text-foreground">Usuário</p>
              <p className="text-xs text-foreground-muted">Conta Premium</p>
            </div>
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gold/10 border border-gold/20">
              <User className="h-4 w-4 text-gold" />
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
