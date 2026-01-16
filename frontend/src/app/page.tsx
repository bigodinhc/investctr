import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">InvestCTR</h1>
        <p className="text-muted-foreground mb-8">
          Plataforma de Gestão de Investimentos Pessoais
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/auth/login"
            className="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            Entrar
          </Link>
          <Link
            href="/auth/register"
            className="px-6 py-3 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/90 transition-colors"
          >
            Criar Conta
          </Link>
        </div>
      </div>
    </main>
  );
}
