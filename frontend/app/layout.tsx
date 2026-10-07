import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';

export const metadata: Metadata = {
  title: 'Enterprise RAG',
  description: 'Enterprise document RAG system',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-page text-ink antialiased">{children}</body>
    </html>
  );
}
