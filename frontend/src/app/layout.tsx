import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Restaurant Decision Assistant",
  description: "Monorepo frontend skeleton for restaurant review analysis.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

