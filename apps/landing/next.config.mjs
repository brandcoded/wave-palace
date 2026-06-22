/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
  // Dev-only proxy: avoids CORS when fetching the production API from localhost.
  // rewrites() is ignored by `next build --output export`.
  async rewrites() {
    return [
      {
        source: "/api-proxy/:path*",
        destination: "https://api.wavepalace.live/:path*",
      },
    ];
  },
};

export default nextConfig;
