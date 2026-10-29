import { defineConfig, loadEnv } from 'vite'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  // Addresses of the Python services, from frontend/.env
  const env = loadEnv(mode, process.cwd(), '')
  const qna = env.QNA_SERVICE_URL || 'http://127.0.0.1:5000'
  const resume = env.RESUME_SERVICE_URL || 'http://127.0.0.1:8000'

  return {
    plugins: [tailwindcss()],
    server: {
      proxy: {
        '/generate': qna,
        '/download': qna,
        '/api': resume,
      },
    },
  }
})
