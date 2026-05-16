import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Casa Segura — Analiza tu contrato antes de firmar",
  description:
    "Revisa un contrato de compraventa o arrendamiento con apoyo de IA antes de firmar. Esto no reemplaza asesoría legal.",
  /** Smoke: bump value to confirm Vercel picked up a new production deploy. */
  other: {
    "casa-segura-deploy-check": "fe-layout-meta-20260516a",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-dvh flex flex-col">{children}</body>
    </html>
  );
}
