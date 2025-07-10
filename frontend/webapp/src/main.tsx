import React, { Suspense } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css' // Estilos globais
import { BrowserRouter } from 'react-router-dom'
import './i18n'; // Importa a configuração do i18next
// import { AuthProvider } from './contexts/AuthContext' // Descomentar quando o AuthContext for criado

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Suspense fallback="Loading..."> {/* Fallback enquanto as traduções carregam */}
      <BrowserRouter>
        {/* <AuthProvider> */}
          <App />
        {/* </AuthProvider> */}
      </BrowserRouter>
    </Suspense>
  </React.StrictMode>,
)
