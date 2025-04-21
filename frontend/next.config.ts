import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  images: {
    domains: ['192.168.56.1', 'localhost'],
    remotePatterns: [
      {
        protocol: 'http',
        hostname: '192.168.56.1',
        port: '8003',
        pathname: '/**',
      },
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8003',
        pathname: '/**',
      },
    ],
  },
};

export default nextConfig;
