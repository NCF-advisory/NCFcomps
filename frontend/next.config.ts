import type { NextConfig } from "next";

// Le front proxifie /api/* vers le backend FastAPI : même origine -> cookies de
// session sans CORS. BACKEND_URL surchargable (docker-compose : http://api:8000).
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Pas d'indicateur de dev Next.js (le badge « N » en bas à gauche recouvrait
  // le bouton Déconnexion ; il n'apparaît de toute façon jamais en production).
  devIndicators: false,
  // Build autonome (deploy/Dockerfile.front) : serveur node intégré, image légère.
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
};

export default nextConfig;
