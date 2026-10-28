import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MolDeNovo AI",
  description: "An evidence-grounded medicinal chemistry copilot",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}