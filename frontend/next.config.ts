import type { NextConfig } from "next";

// Le front proxifie /api/* vers le backend FastAPI : même origine -> cookies de
// session sans CORS. BACKEND_URL surchargable (docker-compose : http://api:8000).
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
};

export default nextConfig;
