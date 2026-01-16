import type { Metadata } from "next";
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

export const metadata: Metadata = {
  title: "InvestCTR - Gestão de Investimentos",
  description: "Plataforma de gestão de investimentos pessoais",
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
