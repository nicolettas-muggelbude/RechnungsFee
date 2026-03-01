import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { execSync } from 'child_process'

function getAppVersion(): string {
  // GitHub Actions: Tag-Name aus Umgebungsvariable (z.B. 'v0.1.0-beta' → '0.1.0-beta')
  if (process.env.GITHUB_REF_NAME) {
    return process.env.GITHUB_REF_NAME.replace(/^v/, '')
  }
  try {
    // Lokal: letzter Git-Tag
    const tag = execSync('git describe --tags --abbrev=0', { encoding: 'utf-8' }).trim()
    return tag.replace(/^v/, '')
  } catch {
    try {
      // Kein Tag vorhanden: kurzer Commit-Hash
      const hash = execSync('git rev-parse --short HEAD', { encoding: 'utf-8' }).trim()
      return `dev-${hash}`
    } catch {
      return 'dev'
    }
  }
}

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(getAppVersion()),
  },
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8001',
    },
  },
})
