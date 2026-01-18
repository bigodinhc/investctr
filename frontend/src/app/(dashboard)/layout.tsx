import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { PageErrorBoundary } from "@/components/error-boundary";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gradient-mesh relative">
      {/* Noise overlay for texture */}
      <div className="fixed inset-0 pointer-events-none bg-noise opacity-[0.02]" />

      <Sidebar />
      <div className="lg:pl-64 transition-all duration-300">
        <Header />
        <main className="p-6 lg:p-8 relative">
          <PageErrorBoundary>{children}</PageErrorBoundary>
        </main>
      </div>
    </div>
  );
}
