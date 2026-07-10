import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DataForge AI | Dataset Production Pipeline",
  description: "Enterprise-grade AI data engineering pipeline for collecting, cleaning, deduplicating, and normalizing training & evaluation datasets.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}
