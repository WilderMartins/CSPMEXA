import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000, // Porta para o servidor de desenvolvimento do frontend
    // Proxy para o API Gateway para evitar problemas de CORS em desenvolvimento
    proxy: {
      // Ex: se o frontend faz uma chamada para /api/v1/gateway/auth/google/login
      // e o API Gateway está em http://localhost:8050
      // e os endpoints do gateway já são /api/v1/*
      // então o proxy deve ser para o base path do gateway.
      // O path da requisição do frontend será mantido após o target.
      // Se o frontend chamar /api/v1/auth/google/login (sem o /gateway no meio)
      // e o gateway expõe /api/v1/auth/google/login, então o proxy está correto.
      // No nosso gateway, os routers são incluídos com prefixo /api/v1.
      // Ex: app.include_router(auth_router.router, prefix=settings.API_V1_STR, tags=["Authentication"])
      // settings.API_V1_STR é "/api/v1".
      // Então, os endpoints do gateway são como: /api/v1/auth/google/login
      // Se o frontend chamar /api/v1/auth/google/login, o proxy para target 'http://localhost:8050'
      // resultará em http://localhost:8050/api/v1/auth/google/login, o que é correto.
      '/api/v1': {
        target: 'http://localhost:8050',
        changeOrigin: true,
        // Se o gateway não tivesse o prefixo /api/v1 em seus endpoints,
        // e quiséssemos que o frontend chamasse /api/v1/* e isso fosse mapeado para /* no gateway
        // aí usaríamos rewrite: (path) => path.replace(/^\/api\/v1/, '')
        // Mas como ambos usam /api/v1, não precisamos de rewrite.
      }
    }
  }
})
