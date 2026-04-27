import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

const apiTarget = process.env.VITE_API_URL ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icons/apple-touch-icon.png'],
      manifest: {
        name: 'Nederlands Leren',
        short_name: 'NL Leren',
        description: 'Dutch language learning app for Spanish speakers (A0–A2)',
        theme_color: '#2563eb',
        background_color: '#0f172a',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '/',
        scope: '/',
        icons: [
          {
            src: '/icons/icon-192x192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: '/icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        // Precache all build assets
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        // Runtime caching strategies
        runtimeCaching: [
          {
            // Vocabulary and grammar: stale-while-revalidate (content changes infrequently)
            urlPattern: /^https?:\/\/.*\/api\/v1\/(vocabulary|grammar)(\/.*)?$/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'api-content-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24, // 24 hours
              },
            },
          },
          {
            // Exercises and progress: network-first (real-time data)
            urlPattern: /^https?:\/\/.*\/api\/v1\/(exercises|progress)(\/.*)?$/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-live-cache',
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 5, // 5 minutes fallback
              },
              networkTimeoutSeconds: 10,
            },
          },
          {
            // Audio files: cache-first (immutable once generated)
            urlPattern: /^https?:\/\/.*\/audio\/.*/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'audio-cache',
              expiration: {
                maxEntries: 200,
                maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
              },
            },
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/audio': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
