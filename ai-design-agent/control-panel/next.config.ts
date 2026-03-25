import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Allow images from localhost backend
  images: {
    remotePatterns: [
      { protocol: 'http', hostname: 'localhost' }
    ]
  }
}

export default nextConfig