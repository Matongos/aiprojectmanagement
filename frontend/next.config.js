/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  images: {
    domains: ['localhost'],
  },
  // Ensure output is set to export for static builds if needed
  // output: 'export',
}

module.exports = nextConfig 