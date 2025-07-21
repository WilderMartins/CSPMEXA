import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom'; // LoginPage usa useLocation
import LoginPage from '../pages/LoginPage';
import { I18nextProvider, useTranslation } from 'react-i18next';
import i18n from '../i18n'; // Nossa configuração i18n
import { vi } from 'vitest';

// Mock do useTranslation
vi.mock('react-i18next', async () => {
  const originalModule = await vi.importActual('react-i18next');
  return {
    ...originalModule,
    useTranslation: () => ({
      t: (key: string, options?: any) => {
        if (key === 'loginPage.title') return 'Login';
        if (key === 'loginPage.greeting') return 'Welcome! Please log in to continue.';
        if (key === 'loginPage.button') return 'Login with Google';
        if (key === 'loginPage.redirectMessage') return 'You will be redirected to Google.';
        if (key === 'loginPage.errorMessage' && options) return `Error: ${options.error}`;
        return key; // Retorna a chave se não houver tradução mockada
      },
      i18n: {
        changeLanguage: vi.fn(),
        language: 'en',
      },
    }),
  };
});


describe('LoginPage', () => {
  it('renders the login page with title and Google login link', () => {
    render(
      <BrowserRouter>
        <I18nextProvider i18n={i18n}> {/* Necessário se o componente usar i18n diretamente */}
          <LoginPage />
        </I18nextProvider>
      </BrowserRouter>
    );

    // Verifica o título (usando o valor mockado da tradução)
    expect(screen.getByText('Login')).toBeInTheDocument();

    // Verifica a saudação
    expect(screen.getByText('Welcome! Please log in to continue.')).toBeInTheDocument();

    // Verifica o link/botão de login do Google
    const loginLink = screen.getByText('Login with Google');
    expect(loginLink).toBeInTheDocument();
    expect(loginLink.closest('a')).toHaveAttribute('href', '/api/v1/auth/google/login');
  });

  it('displays an error message if error query param is present', () => {
    // Simular a presença de query param 'error'
    // O BrowserRouter não permite setar search params diretamente no teste de forma fácil.
    // Uma forma é mockar useLocation.
    vi.mock('react-router-dom', async () => {
        const actual = await vi.importActual('react-router-dom');
        return {
            ...actual,
            useLocation: () => ({
                pathname: '/',
                search: '?error=auth_failed',
                hash: '',
                state: null,
            }),
        };
    });

    render(
      <BrowserRouter>
        <I18nextProvider i18n={i18n}>
          <LoginPage />
        </I18nextProvider>
      </BrowserRouter>
    );

    // Verifica a mensagem de erro (usando o valor mockado da tradução)
    expect(screen.getByText('Error: auth_failed')).toBeInTheDocument();

    // Restaurar o mock de useLocation se outros testes no mesmo arquivo precisarem do original
    vi.restoreAllMocks();
  });
});

// Adicionar setup para jsdom se não estiver globalmente no vitest.config.ts
// Exemplo: import '@testing-library/jest-dom' para ter acesso a toBeInTheDocument etc.
// Geralmente, isso é feito em um arquivo de setup de teste.
// No CI, o `npm install jsdom` é feito. No `vite.config.ts` ou `vitest.config.ts`,
// o `test.environment = 'jsdom'` deve estar configurado.
// E `test.globals = true` ou importar `describe, it, expect` de `vitest`.
// Também `test.setupFiles` para carregar mocks globais ou extensores de expect.
// Assumindo que a configuração do Vitest no projeto já lida com isso.
// O `npm run lint` no CI também adiciona `@vitejs/plugin-react` e `jsdom`.
// O `npm test -- --run` no CI instala vitest, @vitejs/plugin-react, jsdom.
// O `eslint.config.js` na raiz do frontend pode precisar ser ajustado para `vitest/globals`.

// Para que `toBeInTheDocument` funcione, é comum adicionar
// `import '@testing-library/jest-dom/vitest';` em um arquivo de setup de testes
// ou no topo do arquivo de teste.
// Para o CI, o `npm install --save-dev @testing-library/jest-dom` seria necessário.
// Vou adicionar o import aqui para garantir.
import '@testing-library/jest-dom/vitest';
import { describe, it, expect, vi } from 'vitest'; // Importar explicitamente de vitest
