import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'CivicOps AI - Report Infrastructure Issues',
  description: 'Submit citizen infrastructure complaints with photo, voice, and location',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}