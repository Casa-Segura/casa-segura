import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { DISCLAIMER_SHORT } from "@/legal/disclaimer";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Casa Segura — Analiza tu contrato antes de firmar",
  description: `Revisa un contrato de compraventa o arrendamiento con apoyo de IA antes de firmar. ${DISCLAIMER_SHORT}.`,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-dvh flex flex-col touch-manipulation [-webkit-tap-highlight-color:transparent]">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[1000] focus:rounded-[var(--radius-input)] focus:bg-surface focus:px-4 focus:py-3 focus:text-base focus:font-medium focus:text-text-primary focus:shadow-lg focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-accent"
        >
          Saltar al contenido principal
        </a>
        {children}
      </body>
    </html>
  );
}
