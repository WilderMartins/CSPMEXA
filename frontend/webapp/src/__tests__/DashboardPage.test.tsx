import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import DashboardPage from '../pages/DashboardPage';
import { I18nextProvider } from 'react-i18next';
import i18n from '../i18n';
import { vi } from 'vitest';
import axios from 'axios'; // Para mockar o apiClient

// Mock do useTranslation
vi.mock('react-i18next', async () => {
  const originalModule = await vi.importActual('react-i18next');
  return {
    ...originalModule,
    useTranslation: () => ({
      t: (key: string, options?: any) => {
        if (key === 'dashboardPage.title') return 'Dashboard';
        if (key === 'dashboardPage.welcomeMessage') return `Welcome, ${options?.userId || 'User'}!`;
        if (key === 'dashboardPage.fetchAllAlertsButton') return 'Fetch All Alerts';
        // Adicionar outras traduções mockadas conforme necessário para a renderização inicial
        return key;
      },
      i18n: {
        changeLanguage: vi.fn(),
        language: 'en',
      },
    }),
  };
});

// Mock do apiClient (instância do axios)
// O DashboardPage cria uma instância do axios internamente.
// Para mockar, podemos mockar o módulo 'axios' inteiro.
vi.mock('axios', async () => {
    const actualAxios = await vi.importActual('axios');
    return {
        ...actualAxios, // Mantém outras exportações do axios se houver
        default: { // Mocka o default export (que é o axios em si)
            create: vi.fn(() => ({ // Mocka a função create
                get: vi.fn((url: string) => {
                    if (url === '/users/me') {
                        return Promise.resolve({ data: { user_id: 'testuser', email: 'test@example.com' } });
                    }
                    if (url.startsWith('/alerts')) { // Para fetchAllAlerts
                        return Promise.resolve({ data: [] }); // Retorna lista vazia de alertas por default
                    }
                    return Promise.resolve({ data: {} }); // Default para outros GETs
                }),
                post: vi.fn(() => Promise.resolve({ data: [] })), // Default para POSTs (análises)
                // Adicionar mocks para put, delete etc. se o DashboardPage os usar
            })),
        }
    };
});


// Mock do localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });


describe('DashboardPage', () => {
  beforeEach(() => {
    // Simular usuário autenticado para cada teste
    localStorageMock.setItem('authToken', 'fake-auth-token');
    // Limpar mocks do axios entre os testes se necessário (especialmente contadores de chamadas)
    // vi.clearAllMocks(); // Cuidado: isso limpa todos os mocks, incluindo useTranslation se não for reinstanciado.
    // É melhor mockar axios.create().get/post individualmente se precisar resetar chamadas.
    // Ou, se o mock de axios for feito com vi.fn() como acima, eles já são resetados por padrão
    // entre os arquivos de teste, mas não entre `it` blocos no mesmo arquivo, a menos que
    // `vi.clearAllMocks()` ou `vi.resetAllMocks()` seja chamado em `beforeEach` ou `afterEach`.
    // Por simplicidade, vamos assumir que os mocks são "frescos" o suficiente para estes testes básicos.
    // Se os testes começarem a interferir, um setup/teardown mais robusto é necessário.
    // Ex: (axios.create().get as ReturnType<typeof vi.fn>).mockClear();
  });

  afterEach(() => {
    localStorageMock.clear();
    vi.restoreAllMocks(); // Restaura mocks para o estado original, útil para useLocation e outros
  });

  it('renders the dashboard title and welcome message', async () => {
    render(
      <BrowserRouter>
        <I18nextProvider i18n={i18n}>
          <DashboardPage />
        </I18nextProvider>
      </BrowserRouter>
    );

    // Verifica o título (usando o valor mockado da tradução)
    expect(await screen.findByText('Dashboard')).toBeInTheDocument();

    // Verifica a mensagem de boas-vindas (após o /users/me ser resolvido)
    // O texto exato depende do mock de useTranslation e da resposta mockada de /users/me
    await waitFor(() => {
      expect(screen.getByText('Welcome, testuser!')).toBeInTheDocument();
    });
  });

  it('renders the "Fetch All Alerts" button', async () => {
    render(
      <BrowserRouter>
        <I18nextProvider i18n={i18n}>
          <DashboardPage />
        </I18nextProvider>
      </BrowserRouter>
    );
    // Espera o botão aparecer, pois a renderização pode ser assíncrona
    expect(await screen.findByText('Fetch All Alerts')).toBeInTheDocument();
  });

  // Adicionar mais testes no futuro:
  // - Clicar em "Fetch All Alerts" e verificar se a API /alerts é chamada.
  // - Clicar em um botão de análise (ex: AWS S3) e verificar se a API /analyze/... é chamada.
  // - Verificar se a tabela de alertas é renderizada corretamente com dados mockados.
  // - Testar a inserção de IDs de projeto e se eles são passados corretamente para a API.
});

import '@testing-library/jest-dom/vitest';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
