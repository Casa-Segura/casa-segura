// No-op: touch file to trigger frontend deployment; safe to remove on the next real change.
import type { Metadata } from "next";
import { Inter, Newsreader, Geist } from "next/font/google";
import { DISCLAIMER_SHORT } from "@/legal/disclaimer";
import "./globals.css";
import { cn } from "@/lib/utils";

const geist = Geist({ subsets: ["latin"], variable: "--font-geist" });

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  display: "swap",
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
    <html
      lang="es"
      className={cn(
        "h-full",
        inter.variable,
        newsreader.variable,
        geist.variable,
        "font-sans",
      )}
    >
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
