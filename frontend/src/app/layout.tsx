import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

// General Sans is not available on Google Fonts; we use Inter Display via
// CSS font-feature-settings and rely on the system "Outfit"-like fallback in
// component styles. If you have a self-hosted General Sans, drop the .woff2
// into /public/fonts/ and add a @font-face rule here.

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Profile Guru — AI DM Intelligence",
  description:
    "High-performance semantic DM indexing, bilingual voice transcription, and personality profiling.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        {/* Apply persisted theme before paint to avoid flash */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                var t = localStorage.getItem('pg.theme');
                if (t === 'light' || t === 'dark') {
                  document.documentElement.setAttribute('data-theme', t);
                } else {
                  document.documentElement.setAttribute('data-theme', 'dark');
                }
              } catch (e) {
                document.documentElement.setAttribute('data-theme', 'dark');
              }
            `,
          }}
        />
      </head>
      <body className="font-sans antialiased bg-background text-foreground h-screen w-screen overflow-hidden relative">
        {/* Skip-to-content link (a11y) */}
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>

        {/* Ambient background accent glows */}
        <div className="ambient-glow ambient-glow-violet -top-40 -left-40" />
        <div className="ambient-glow ambient-glow-cyan -bottom-40 -right-40" />

        <main
          id="main-content"
          tabIndex={-1}
          className="relative z-10 w-full h-full flex flex-col outline-none"
        >
          {children}
        </main>
      </body>
    </html>
  );
}
