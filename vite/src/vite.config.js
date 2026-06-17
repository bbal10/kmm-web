import {defineConfig} from 'vite'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
    server: {
        host: '0.0.0.0',
        port: 5173,
        strictPort: true,
        watch: {
            usePolling: true,
            interval: 100,
        },
        hmr: {
            host: 'localhost',
            port: 5173,
        },
    },
    build: {
        outDir: "../static/dist",
        emptyOutDir: true,
        manifest: true,
    },
    plugins: [
        tailwindcss(),
    ],
})