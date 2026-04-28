import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Trading Website CRM",
  description: "Trading website, user dashboard, and CRM for the Telegram trading bot.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <Link href="/">
            <strong>Trading Platform</strong>
          </Link>
          <nav>
            <Link href="/plans">Plans</Link>
            <Link href="/login">Login</Link>
            <Link href="/dashboard">Dashboard</Link>
            <Link href="/admin">CRM</Link>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
