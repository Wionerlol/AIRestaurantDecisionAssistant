import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Restaurant Decision Assistant",
  description: "Minimal chat UI for the AI Restaurant Decision Assistant backend.",
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
