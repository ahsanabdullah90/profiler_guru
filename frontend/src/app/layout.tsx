import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
});

export const metadata: Metadata = {
  title: "Profile Guru — AI Instagram DM Intelligence",
  description: "High-performance semantic DM indexing, bilingual voice transcription, and personality profiling.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${outfit.variable}`}>
      <body className="font-sans antialiased bg-background text-foreground h-screen w-screen overflow-hidden relative">
        {/* Ambient background accent glows */}
        <div className="ambient-glow ambient-glow-violet -top-40 -left-40" />
        <div className="ambient-glow ambient-glow-cyan -bottom-40 -right-40" />
        
        <main className="relative z-10 w-full h-full flex flex-col">
          {children}
        </main>
      </body>
    </html>
  );
}
