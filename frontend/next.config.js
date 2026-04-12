/** @type {import('next').NextConfig} */
const isVercel = !!process.env.VERCEL;

const nextConfig = {
  reactStrictMode: true,

  // On Vercel: proxy API calls to the deployed FastAPI backend via env var.
  // Locally: falls back to http://localhost:8000
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      // WebSocket proxying is NOT supported on Vercel Edge Network.
      // On Vercel, the frontend connects directly to NEXT_PUBLIC_WS_URL.
      // Only proxy WS in local dev.
      ...(!isVercel
        ? [
            {
              source: "/ws/:path*",
              destination: `${
                process.env.BACKEND_WS_URL ?? "ws://localhost:8000"
              }/ws/:path*`,
            },
          ]
        : []),
    ];
  },

  images: {
    remotePatterns: [
      { protocol: "https", hostname: "avatars.githubusercontent.com" },
      { protocol: "https", hostname: "github.com" },
    ],
  },

  experimental: {
    serverActions: {
      // Allow the Vercel deployment URL + localhost
      allowedOrigins: [
        "localhost:3000",
        process.env.VERCEL_URL ?? "",
        process.env.NEXT_PUBLIC_APP_URL?.replace(/^https?:\/\//, "") ?? "",
      ].filter(Boolean),
    },
  },
};

module.exports = nextConfig;
