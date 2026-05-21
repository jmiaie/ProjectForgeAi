/** @type {import('next').NextConfig} */
const apiProxy = process.env.API_PROXY_TARGET || 'http://localhost:8000';

const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${apiProxy}/api/:path*`,
      },
      {
        source: '/health',
        destination: `${apiProxy}/health`,
      },
    ];
  },
};

export default nextConfig;
