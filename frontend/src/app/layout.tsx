import type { Metadata } from "next";
import { Inter, Space_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["400", "500", "600", "700"],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: {
    default: "InvestCTR - Gestao de Investimentos",
    template: "%s | InvestCTR",
  },
  description: "Plataforma de gestao de investimentos pessoais. Acompanhe seu portfolio, calcule rentabilidade e gerencie suas cotas.",
  keywords: ["investimentos", "portfolio", "acoes", "fundos", "rentabilidade", "gestao financeira"],
  authors: [{ name: "InvestCTR" }],
  creator: "InvestCTR",
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || "https://investctr.vercel.app"),
  openGraph: {
    type: "website",
    locale: "pt_BR",
    siteName: "InvestCTR",
    title: "InvestCTR - Gestao de Investimentos",
    description: "Plataforma de gestao de investimentos pessoais. Acompanhe seu portfolio, calcule rentabilidade e gerencie suas cotas.",
  },
  twitter: {
    card: "summary",
    title: "InvestCTR - Gestao de Investimentos",
    description: "Plataforma de gestao de investimentos pessoais",
  },
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
    ],
    apple: "/favicon.svg",
  },
  manifest: "/site.webmanifest",
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#0A0A0B" },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" suppressHydrationWarning className="dark">
      <body
        className={`${inter.variable} ${spaceGrotesk.variable} ${jetbrainsMono.variable} font-sans bg-background-deep min-h-screen`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
