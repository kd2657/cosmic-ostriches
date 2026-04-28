import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "The Local Minima",
  description: "A News Narrative Explorer powered by Semantic Clustering",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                function scrollZoomSuppressor(event) {
                  var reason = event.reason;
                  var msg = (reason && reason.message) ? reason.message : String(reason || '');
                  if (msg.indexOf('_scrollZoom') !== -1) {
                    event.preventDefault();
                    event.stopImmediatePropagation();
                  }
                }
                // Use capture phase (true) so this fires BEFORE Next.js's internal error reporter
                window.addEventListener('unhandledrejection', scrollZoomSuppressor, true);
              })();
            `,
          }}
        />
      </head>
      <body className="min-h-full flex flex-col">
        <div className="fixed top-4 left-4 z-50">
          <Link href="/about" className="text-xs font-mono text-neutral-500 hover:text-neutral-300 transition-colors">
            [ ABOUT ]
          </Link>
        </div>
        {children}
      </body>
    </html>
  );
}
