"use client";

import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { LogOut, Bell, Search, User, Menu } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { CommandPalette } from "@/components/shared/CommandPalette";
import { cn } from "@/lib/utils";

const pageNames: Record<string, string> = {
  "/dashboard": "DASHBOARD",
  "/accounts": "CONTAS",
  "/positions": "POSIÇÕES",
  "/transactions": "TRANSAÇÕES",
  "/documents": "DOCUMENTOS",
  "/cash-flows": "APORTES/SAQUES",
  "/settings": "CONFIGURAÇÕES",
};

export function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const [commandOpen, setCommandOpen] = useState(false);

  // Keyboard shortcut for Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandOpen((open) => !open);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

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
    <header className="sticky top-0 z-40 h-16 border-b border-border bg-background-elevated">
      <div className="flex h-full items-center justify-between px-6">
        {/* Left: Mobile menu + Page title */}
        <div className="flex items-center gap-4">
          {/* Mobile menu button */}
          <button
            aria-label="Abrir menu de navegação"
            className="lg:hidden p-2 rounded-md hover:bg-background-surface transition-colors"
          >
            <Menu className="h-5 w-5 text-foreground-muted" />
          </button>

          {/* Mobile logo */}
          <span className="lg:hidden font-display text-xl text-foreground tracking-wider">
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
          <button
            onClick={() => setCommandOpen(true)}
            className="flex w-full items-center gap-2 rounded-lg bg-background-surface px-4 py-2 text-sm text-foreground-muted hover:bg-background transition-colors"
            aria-label="Abrir busca global (Ctrl+K)"
          >
            <Search className="h-4 w-4" />
            <span>Buscar...</span>
            <kbd className="pointer-events-none ml-auto inline-flex h-5 select-none items-center gap-1 rounded border border-border bg-background px-1.5 font-mono text-[10px] font-medium text-foreground-muted">
              <span className="text-xs">Ctrl</span>K
            </kbd>
          </button>
        </div>

        {/* Command Palette */}
        <CommandPalette open={commandOpen} onOpenChange={setCommandOpen} />

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          {/* Notifications */}
          <button
            aria-label="Ver notificações"
            className="relative p-2 rounded-md hover:bg-background-surface transition-colors group"
          >
            <Bell className="h-5 w-5 text-foreground-muted group-hover:text-foreground transition-colors" />
            {/* Notification dot */}
            <span className="absolute top-1.5 right-1.5 h-2 w-2 bg-foreground rounded-full" aria-hidden="true" />
          </button>

          {/* User menu */}
          <div className="flex items-center gap-3 pl-3 ml-2 border-l border-border">
            <div className="hidden sm:block text-right">
              <p className="text-sm font-medium text-foreground">Usuário</p>
              <p className="text-xs text-foreground-muted">Conta Premium</p>
            </div>
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-background-surface border border-border">
              <User className="h-4 w-4 text-foreground-muted" />
            </div>
          </div>

          {/* Sign out */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleSignOut}
            aria-label="Sair da conta"
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
