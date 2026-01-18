"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Briefcase,
  ArrowRightLeft,
  FileText,
  Wallet,
  Settings,
  TrendingUp,
  ChevronLeft,
  ChevronRight,
  Building2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Contas", href: "/accounts", icon: Building2 },
  { name: "Posições", href: "/positions", icon: Briefcase },
  { name: "Transações", href: "/transactions", icon: ArrowRightLeft },
  { name: "Documentos", href: "/documents", icon: FileText },
  { name: "Aportes/Saques", href: "/cash-flows", icon: Wallet },
];

const secondaryNavigation = [
  { name: "Configurações", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-50 bg-background-elevated border-r border-border hidden lg:flex lg:flex-col transition-all duration-300",
        collapsed ? "w-20" : "w-64"
      )}
    >
      {/* Logo Section */}
      <div className="flex h-16 items-center justify-between px-4 border-b border-border">
        <Link
          href="/dashboard"
          className={cn(
            "flex items-center gap-3 transition-all duration-300",
            collapsed && "justify-center"
          )}
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-foreground/10 border border-border">
            <TrendingUp className="h-5 w-5 text-foreground" />
          </div>
          {!collapsed && (
            <span className="font-display text-2xl text-foreground tracking-wider">
              INVESTCTR
            </span>
          )}
        </Link>
        <button
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? "Expandir menu lateral" : "Recolher menu lateral"}
          className={cn(
            "p-1.5 rounded-md hover:bg-background-surface transition-colors text-foreground-muted hover:text-foreground",
            collapsed && "absolute -right-3 top-6 bg-background-elevated border border-border shadow-lg"
          )}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "group relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
                collapsed && "justify-center px-2",
                isActive
                  ? "bg-background-surface text-foreground"
                  : "text-foreground-muted hover:bg-background-surface hover:text-foreground"
              )}
            >
              {/* Active indicator */}
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-foreground rounded-r-full" />
              )}

              <item.icon
                className={cn(
                  "h-5 w-5 shrink-0 transition-colors",
                  isActive ? "text-foreground" : "text-foreground-muted group-hover:text-foreground"
                )}
              />

              {!collapsed && (
                <span className="truncate">{item.name}</span>
              )}

              {/* Tooltip for collapsed state */}
              {collapsed && (
                <div className="absolute left-full ml-2 px-2 py-1 bg-background-elevated border border-border rounded-md text-sm whitespace-nowrap opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
                  {item.name}
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Divider */}
      <div className="mx-3 border-t border-border" />

      {/* Secondary Navigation */}
      <nav className="p-3 space-y-1">
        {secondaryNavigation.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "group relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
                collapsed && "justify-center px-2",
                isActive
                  ? "bg-background-surface text-foreground"
                  : "text-foreground-muted hover:bg-background-surface hover:text-foreground"
              )}
            >
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-foreground rounded-r-full" />
              )}

              <item.icon
                className={cn(
                  "h-5 w-5 shrink-0 transition-colors",
                  isActive ? "text-foreground" : "text-foreground-muted group-hover:text-foreground"
                )}
              />

              {!collapsed && (
                <span className="truncate">{item.name}</span>
              )}

              {collapsed && (
                <div className="absolute left-full ml-2 px-2 py-1 bg-background-elevated border border-border rounded-md text-sm whitespace-nowrap opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
                  {item.name}
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Version Badge */}
      {!collapsed && (
        <div className="p-4 border-t border-border">
          <div className="flex items-center justify-between text-xs text-foreground-dim">
            <span>v1.0.0 MVP</span>
            <span className="px-1.5 py-0.5 rounded bg-background-surface text-foreground-muted text-[10px] font-medium">
              BETA
            </span>
          </div>
        </div>
      )}
    </aside>
  );
}
