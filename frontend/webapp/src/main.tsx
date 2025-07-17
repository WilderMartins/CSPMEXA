import React, { Suspense } from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';
import './index.css'; // Estilos globais
import { BrowserRouter } from 'react-router-dom';
import './i18n'; // Importa a configuração do i18next
import { AuthProvider } from './contexts/AuthContext';
import { AccountProvider } from './contexts/AccountContext';
import { MantineProvider } from '@mantine/core'; // Importar MantineProvider
import { Notifications } from '@mantine/notifications';
import '@mantine/core/styles.css'; // Importar estilos core da Mantine
import '@mantine/notifications/styles.css';


ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MantineProvider
      theme={{
        fontFamily: 'Verdana, sans-serif', // Exemplo de alteração de fonte
        primaryColor: 'teal', // Exemplo de cor primária (Mantine tem 'teal' como uma cor nomeada)
        defaultRadius: 'md', // Exemplo: 'xs', 'sm', 'md', 'lg', 'xl' ou número
        // Você pode adicionar mais customizações aqui:
        // colors: {
        //   'ocean-blue': ['#7AD1DD', '#5FCCDB', '#44CADC', '#2AC9DE', '#1AC2D9', '#11B7CD', '#09ADC3', '#0E99AC', '#128797', '#147885'],
        //   'bright-pink': ['#F0BBDD', '#ED9BCF', '#EC7CC3', '#ED5DB8', '#F13EAF', '#F71FA7', '#FF00A1', '#E00890', '#C50E82', '#AD1374'],
        // },
        // components: {
        //   Button: {
        //     defaultProps: {
        //       size: 'sm',
        //     }
        //   }
        // }
      }}
      defaultColorScheme="auto"
    >
      <Notifications />
      <Suspense fallback="Loading..."> {/* Fallback enquanto as traduções carregam */}
        <BrowserRouter>
          <AuthProvider>
            <AccountProvider>
              <App />
            </AccountProvider>
          </AuthProvider>
        </BrowserRouter>
      </Suspense>
    </MantineProvider>
  </React.StrictMode>,
)
