import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI-Driven Quantitative Trading System",
  description: "AI 雙因子量化回測系統",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-Hant">
      <body>{children}</body>
    </html>
  );
}
