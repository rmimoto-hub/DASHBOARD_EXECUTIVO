import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "dir-dashboard — KAMI CO.",
  description: "Painel de gestao executiva",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
