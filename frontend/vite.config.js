import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.png', 'robots.txt'],
      manifest: {
        name: 'Báo Tổng Hợp Rủi Ro Thiên Tai',
        short_name: 'VietDisaster',
        description: 'Hệ thống giám sát và tổng hợp tin tức thiên tai Việt Nam',
        theme_color: '#ffffff',
        background_color: '#ffffff',
        display: 'standalone',
        orientation: 'portrait',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,json}']
      }
    })
  ],
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 1600,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
             if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) {
               return 'vendor-react';
             }
             if (id.includes('recharts')) {
               return 'vendor-charts';
             }
             if (id.includes('leaflet') || id.includes('react-leaflet')) {
               return 'vendor-maps';
             }
             if (id.includes('lucide-react')) {
               return 'vendor-icons';
             }
             return 'vendor-utils';
          }
        },
      },
    },
  },
})
