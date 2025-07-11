import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

import { defineConfig, loadEnv } from 'vite'; // Adicionado loadEnv
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Carrega variáveis de ambiente do .env, .env.development, .env.production
  // O terceiro argumento '' significa que todas as variáveis são carregadas, não apenas as prefixadas com VITE_.
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [react()],
    server: {
      port: 3000, // Porta para o servidor de desenvolvimento do frontend
      host: '0.0.0.0', // Importante para Docker: escutar em todas as interfaces
      proxy: {
        // Proxy para o API Gateway para evitar problemas de CORS em desenvolvimento.
        // Usado apenas por `npm run dev`. Em produção, o Nginx lida com isso.
        '/api/v1': {
          // A URL do API Gateway para desenvolvimento.
          // Pode ser lida de uma variável de ambiente .env local, ex: VITE_DEV_API_PROXY_TARGET
          target: env.VITE_DEV_API_PROXY_TARGET || 'http://localhost:8050',
          changeOrigin: true,
          // secure: false, // Se o backend (API Gateway) não tiver HTTPS em dev
        }
      }
    },
    // Configurações de Build (para `npm run build`)
    build: {
      outDir: 'dist', // Pasta de saída padrão
      // sourcemap: true, // Opcional: gerar sourcemaps para produção
    },
    // Define variáveis de ambiente globais acessíveis no código do cliente via import.meta.env.
    // Estas são injetadas NO MOMENTO DO BUILD.
    define: {
      // Exemplo: 'import.meta.env.VITE_API_BASE_URL': JSON.stringify(env.VITE_API_BASE_URL || '/api/v1')
      // Para a configuração atual do docker-compose.yml, VITE_API_BASE_URL é passado como build arg.
      // O Dockerfile do frontend precisa ser ajustado para usar este build arg
      // e defini-lo como uma variável de ambiente para o processo de build do Vite.
      // Se VITE_API_BASE_URL for definido como build arg, não precisa ser redefinido aqui
      // a menos que você queira um fallback se o build arg não for passado.
      // Se o Nginx for fazer proxy de /api/v1, então o base URL no código JS pode ser relativo: '/api/v1'.
      // Se o docker-compose.yml passa `args: VITE_API_BASE_URL: http://localhost:${API_GATEWAY_PORT:-8050}/api/v1`
      // e o Dockerfile do frontend usa este ARG para definir uma ENV var para o build do Vite,
      // então o código do frontend pode usar `import.meta.env.VITE_API_BASE_URL`.
      // Exemplo de como o Dockerfile do frontend poderia fazer isso:
      // ARG VITE_API_BASE_URL_ARG=/api/v1
      // ENV VITE_API_BASE_URL=$VITE_API_BASE_URL_ARG
      // RUN npm run build
      //
      // Se o Nginx sempre fizer proxy de /api/v1, então o frontend pode ter hardcoded /api/v1 ou
      // usar uma VITE_API_BASE_URL configurada para /api/v1.
      // Para a configuração com Nginx fazendo proxy (nginx.default.conf), o frontend
      // deve fazer chamadas para /api/v1/... (relativo ao seu próprio host).
      // Então, o VITE_API_BASE_URL no código JS deve ser '/api/v1'.
      // Vamos definir isso aqui para clareza, assumindo que o Nginx fará o proxy.
      'import.meta.env.VITE_API_BASE_URL': JSON.stringify(env.VITE_API_BASE_URL || '/api/v1')
    }
  };
});
