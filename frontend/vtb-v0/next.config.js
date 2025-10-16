/** @type {import('next').NextConfig} */
const nextConfig = {
  images: { unoptimized: true },
  async rewrites() {
    // Проверяем переменную окружения для ngrok backend URL
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    
    return [
      { source: '/api/:path*', destination: `${backendUrl}/api/:path*` },
      { source: '/auth/:path*', destination: `${backendUrl}/auth/:path*` },
      { source: '/ws/:path*', destination: `${backendUrl}/ws/:path*` },
    ];
  },
};

module.exports = nextConfig;
