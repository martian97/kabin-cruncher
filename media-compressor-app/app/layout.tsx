import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "Kabin Cruncher",
  description: "Kabin Cruncher — hosted on Railway, built to take your heavy image and video files out back and handle them. Upload, crunch, and download share-ready media in seconds."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

