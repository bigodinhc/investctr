import type { Metadata, Viewport } from "next";
import { Inter, Bebas_Neue, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const bebasNeue = Bebas_Neue({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-bebas",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: "#00d4aa",
};

export const metadata: Metadata = {
  title: {
    default: "InvestCTR - Gestao de Investimentos",
    template: "InvestCTR | %s",
  },
  description: "Plataforma de gestao de investimentos pessoais",
  keywords: ["investimentos", "portfolio", "acoes", "fundos", "renda fixa", "gestao financeira"],
  authors: [{ name: "InvestCTR" }],
  creator: "InvestCTR",
  metadataBase: new URL("https://investctr.com"),
  manifest: "/manifest.json",
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/icon.svg", type: "image/svg+xml", sizes: "any" },
    ],
    apple: [
      { url: "/apple-touch-icon.svg", type: "image/svg+xml" },
    ],
  },
  openGraph: {
    type: "website",
    locale: "pt_BR",
    url: "https://investctr.com",
    siteName: "InvestCTR",
    title: "InvestCTR - Gestao de Investimentos",
    description: "Plataforma de gestao de investimentos pessoais. Acompanhe seu portfolio, analise performance e tome decisoes informadas.",
    images: [
      {
        url: "/icon.svg",
        width: 512,
        height: 512,
        alt: "InvestCTR Logo",
      },
    ],
  },
  twitter: {
    card: "summary",
    title: "InvestCTR - Gestao de Investimentos",
    description: "Plataforma de gestao de investimentos pessoais. Acompanhe seu portfolio, analise performance e tome decisoes informadas.",
    images: ["/icon.svg"],
  },
  robots: {
    index: true,
    follow: true,
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "InvestCTR",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" suppressHydrationWarning className="dark">
      <body
        className={`${inter.variable} ${bebasNeue.variable} ${jetbrainsMono.variable} font-sans bg-background-deep min-h-screen`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
