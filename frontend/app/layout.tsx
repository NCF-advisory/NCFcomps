import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

/* Charte « Institutionnel clair v2 » : Inter est l'unique famille typographique
   (pas de serif, pas de seconde famille). Graisses chargées : 400 à 900. */
const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800", "900"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "NCF · Comparables & Évaluation",
  description: "Outil interne d'évaluation : comparables boursiers et cessions de fonds de commerce.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={inter.variable}>
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
