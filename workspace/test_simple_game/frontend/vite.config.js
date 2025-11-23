import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * @file Vite configuration file.
 * @see https://vitejs.dev/config/
 */

export default defineConfig({
  /**
   * An array of Vite plugins to use.
   * @see https://vitejs.dev/plugins/
   */
  plugins: [
    /**
     * @vitejs/plugin-react enables React support.
     * It provides features like Fast Refresh (HMR) and automatic JSX runtime.
     * @see https://github.com/vitejs/vite-plugin-react
     */
    react(),
  ],

  /**
   * Configuration for the development server.
   * @see https://vitejs.dev/config/server-options.html
   */
  server: {
    /**
     * The port the development server will listen on.
     */
    port: 5173,

    /**
     * Proxy settings for the development server.
     * This is used to forward API requests from the frontend dev server
     * to the backend API server, avoiding CORS issues during development.
     */
    proxy: {
      // Proxy requests from /api to the backend server running on localhost:8000
      '/api': {
        /**
         * The target URL of the backend server.
         * Assumes the FastAPI backend is running on http://localhost:8000.
         */
        target: 'http://localhost:8000',

        /**
         * Changes the origin of the host header to the target URL.
         * This is necessary for some backend servers that validate the Host header.
         */
        changeOrigin: true,

        /**
         * Rewrites the request path.
         * This removes the '/api' prefix from the request path before forwarding it
         * to the backend. For example, a request to '/api/game/state' will be
         * forwarded to 'http://localhost:8000/game/state'.
         */
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});