import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DataLab OS · Control Plane",
  description: "Live execution viewer for the DataLab OS agentic workflow",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
