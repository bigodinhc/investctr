"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import {
  LayoutDashboard,
  Building2,
  Briefcase,
  ArrowRightLeft,
  FileText,
  Wallet,
  Settings,
  Search,
  TrendingUp,
} from "lucide-react"

import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "@/components/ui/command"

interface CommandPaletteProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const router = useRouter()

  const runCommand = React.useCallback(
    (command: () => void) => {
      onOpenChange(false)
      command()
    },
    [onOpenChange]
  )

  // Navigation items
  const navigationItems = [
    {
      name: "Dashboard",
      href: "/dashboard",
      icon: LayoutDashboard,
      shortcut: "D",
    },
    {
      name: "Contas",
      href: "/accounts",
      icon: Building2,
      shortcut: "C",
    },
    {
      name: "Posicoes",
      href: "/positions",
      icon: Briefcase,
      shortcut: "P",
    },
    {
      name: "Transacoes",
      href: "/transactions",
      icon: ArrowRightLeft,
      shortcut: "T",
    },
    {
      name: "Documentos",
      href: "/documents",
      icon: FileText,
      shortcut: "O",
    },
    {
      name: "Aportes/Saques",
      href: "/cash-flows",
      icon: Wallet,
      shortcut: "A",
    },
    {
      name: "Configuracoes",
      href: "/settings",
      icon: Settings,
      shortcut: "S",
    },
  ]

  // Quick actions
  const quickActions = [
    {
      name: "Novo Upload de Documento",
      action: () => router.push("/documents?action=upload"),
      icon: FileText,
    },
    {
      name: "Nova Movimentacao",
      action: () => router.push("/cash-flows?action=new"),
      icon: Wallet,
    },
    {
      name: "Atualizar Cotacoes",
      action: () => router.push("/positions?action=sync"),
      icon: TrendingUp,
    },
  ]

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Buscar paginas, acoes..." />
      <CommandList>
        <CommandEmpty>
          <div className="flex flex-col items-center gap-2 py-4">
            <Search className="h-8 w-8 text-foreground-muted" />
            <p>Nenhum resultado encontrado.</p>
            <p className="text-xs text-foreground-dim">
              Tente buscar por &quot;dashboard&quot;, &quot;transacoes&quot; ou &quot;contas&quot;
            </p>
          </div>
        </CommandEmpty>
        <CommandGroup heading="Navegacao">
          {navigationItems.map((item) => (
            <CommandItem
              key={item.href}
              value={item.name}
              onSelect={() => runCommand(() => router.push(item.href))}
            >
              <item.icon className="mr-2 h-4 w-4" />
              <span>{item.name}</span>
              <CommandShortcut>
                <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border border-border bg-background-surface px-1.5 font-mono text-[10px] font-medium text-foreground-muted">
                  {item.shortcut}
                </kbd>
              </CommandShortcut>
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Acoes Rapidas">
          {quickActions.map((action) => (
            <CommandItem
              key={action.name}
              value={action.name}
              onSelect={() => runCommand(action.action)}
            >
              <action.icon className="mr-2 h-4 w-4" />
              <span>{action.name}</span>
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
