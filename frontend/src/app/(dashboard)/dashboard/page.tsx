export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="p-6 bg-card border rounded-lg">
          <p className="text-sm text-muted-foreground">NAV Total</p>
          <p className="text-2xl font-bold">R$ 0,00</p>
        </div>
        <div className="p-6 bg-card border rounded-lg">
          <p className="text-sm text-muted-foreground">Valor da Cota</p>
          <p className="text-2xl font-bold">R$ 1,00</p>
        </div>
        <div className="p-6 bg-card border rounded-lg">
          <p className="text-sm text-muted-foreground">Rentabilidade</p>
          <p className="text-2xl font-bold text-green-600">+0,00%</p>
        </div>
        <div className="p-6 bg-card border rounded-lg">
          <p className="text-sm text-muted-foreground">P&L Total</p>
          <p className="text-2xl font-bold">R$ 0,00</p>
        </div>
      </div>

      {/* Chart placeholder */}
      <div className="p-6 bg-card border rounded-lg mb-8">
        <h2 className="text-lg font-semibold mb-4">Evolução do Patrimônio</h2>
        <div className="h-64 flex items-center justify-center text-muted-foreground">
          Gráfico será exibido aqui após importar dados
        </div>
      </div>

      {/* Positions table placeholder */}
      <div className="p-6 bg-card border rounded-lg">
        <h2 className="text-lg font-semibold mb-4">Posições Abertas</h2>
        <div className="text-muted-foreground text-center py-8">
          Nenhuma posição encontrada. Importe um extrato para começar.
        </div>
      </div>
    </div>
  );
}
