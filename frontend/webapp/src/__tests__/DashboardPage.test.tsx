/*
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import DashboardPage from '../pages/DashboardPage';
import { I18nextProvider } from 'react-i18next';
import i18n from '../i18n'; // Sua configuração i18n real
import { vi, describe, it, expect, beforeEach, afterEach, MockedFunction } from 'vitest';
import axios from 'axios'; // Será mockado
import '@testing-library/jest-dom/vitest';

// --- Mocks Globais para o Módulo ---

const mockTranslations: Record<string, string> = {
  'dashboardPage.title': 'Dashboard',
  'dashboardPage.welcomeMessage': 'Welcome, {{userId}}!',
  'dashboardPage.fetchAllAlertsButton': 'Fetch All Alerts',
  'dashboardPage.noAlertsFound': 'No alerts found.',
  'dashboardPage.errorFetchingAllAlerts': 'Error fetching all alerts: {{error}}',
  'dashboardPage.errorNoPermissionToChangeStatus': 'You do not have permission to change the alert status.',
  'dashboardPage.alertStatusUpdatedSuccess': 'Alert {{alertId}} status updated to {{newStatus}}.',
  'dashboardPage.errorUpdatingStatus': 'Error updating status.',
  'dashboardPage.errorUpdatingAlertStatus': 'Error updating status for alert {{alertId}}: {{error}}',
  'alertItem.id': 'ID',
  'alertItem.provider': 'Provider',
  'alertItem.severity': 'Severity',
  'alertItem.title': 'Title',
  'alertItem.resource': 'Resource ID',
  'alertItem.resourceType': 'Resource Type',
  'alertItem.status': 'Status',
  'alertItem.firstSeen': 'First Seen',
  'alertItem.lastSeen': 'Last Seen',
  'alertItem.actions': 'Actions',
  'alertActions.acknowledge': 'Acknowledge',
  'alertActions.resolve': 'Resolve',
  'alertActions.ignore': 'Ignore',
  // Adicionar outras chaves usadas no DashboardPage se houver
  'dashboardPage.loadingAllAlerts': 'Loading Alerts...',
  'dashboardPage.allPersistedAlerts': 'All Persisted Alerts',
  'dashboardPage.alertsFoundFor': 'Alerts found for: {{type}}',
  'dashboardPage.loadingMessage': 'Loading {{type}}...',
};

vi.mock('react-i18next', async () => {
  const originalModule = await vi.importActual<typeof import('react-i18next')>('react-i18next');
  return {
    ...originalModule,
    useTranslation: () => ({
      t: (key: string, options?: any) => {
        let translation = mockTranslations[key] || key;
        if (options) {
          Object.keys(options).forEach(optKey => {
            translation = translation.replace(`{{${optKey}}}`, options[optKey]);
          });
        }
        return translation;
      },
      i18n: {
        changeLanguage: vi.fn(),
        language: 'en',
        isInitialized: true,
        options: {},
        services: { resourceStore: { data: { en: { translation: mockTranslations } } } }
      },
    }),
  };
});

// Mock do apiClient (instância do axios)
const mockAxiosInstance = {
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
};
vi.mock('axios', async () => {
  const actualAxios = await vi.importActual<typeof axios>('axios');
  return {
    ...actualAxios,
    default: {
      ...actualAxios.default,
      create: vi.fn(() => mockAxiosInstance),
    },
  };
});

// Mock do localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value.toString(); },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Helper para renderizar o DashboardPage com mocks
const renderDashboard = (userRole = 'User', initialAlerts: any[] = []) => {
  (mockAxiosInstance.get as MockedFunction<any>).mockImplementation((url: string) => {
    if (url === '/users/me') {
      return Promise.resolve({ data: { user_id: 'testuser', email: 'test@example.com', role: userRole } });
    }
    if (url.startsWith('/alerts')) {
      return Promise.resolve({ data: initialAlerts });
    }
    return Promise.resolve({ data: {} });
  });
  (mockAxiosInstance.post as MockedFunction<any>).mockResolvedValue({ data: [] });
  (mockAxiosInstance.patch as MockedFunction<any>).mockResolvedValue({ data: {} }); // Default para PATCH

  // Mock window.alert
  window.alert = vi.fn();

  return render(
    <BrowserRouter>
      <I18nextProvider i18n={i18n}>
        <DashboardPage />
      </I18nextProvider>
    </BrowserRouter>
  );
};

const sampleAlerts = [
  { id: 1, provider: 'aws', severity: 'High', title: 'S3 Public Bucket', resource_id: 'bucket1', resource_type: 'S3Bucket', status: 'OPEN', first_seen_at: new Date().toISOString(), last_seen_at: new Date().toISOString(), created_at: new Date().toISOString(), updated_at: new Date().toISOString(), description: 'Desc1' },
  { id: 2, provider: 'gcp', severity: 'Medium', title: 'VM Public IP', resource_id: 'vm1', resource_type: 'VMInstance', status: 'ACKNOWLEDGED', first_seen_at: new Date().toISOString(), last_seen_at: new Date().toISOString(), created_at: new Date().toISOString(), updated_at: new Date().toISOString(), description: 'Desc2' },
];


describe('DashboardPage', () => {
  beforeEach(() => {
    localStorageMock.setItem('authToken', 'fake-auth-token');
    // Resetar mocks antes de cada teste
    mockAxiosInstance.get.mockReset();
    mockAxiosInstance.post.mockReset();
    mockAxiosInstance.patch.mockReset();
    (window.alert as MockedFunction<any>).mockClear();
  });

  afterEach(() => {
    localStorageMock.clear();
    vi.restoreAllMocks(); // Restaura todos os mocks para o estado original
  });

  it('renders the dashboard title and welcome message for User role', async () => {
    renderDashboard('User');
    expect(await screen.findByText('Dashboard')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('Welcome, testuser!')).toBeInTheDocument();
    });
  });

  it('fetches and displays alerts on load', async () => {
    renderDashboard('User', sampleAlerts);
    await waitFor(() => {
      expect(screen.getByText('S3 Public Bucket')).toBeInTheDocument();
      expect(screen.getByText('VM Public IP')).toBeInTheDocument();
    });
  });

  describe('Alert Action Buttons RBAC', () => {
    it('does NOT show action buttons for User role', async () => {
      renderDashboard('User', [sampleAlerts[0]]); // Apenas um alerta OPEN
      await waitFor(() => expect(screen.getByText('S3 Public Bucket')).toBeInTheDocument());
      expect(screen.queryByText('Acknowledge')).not.toBeInTheDocument();
      expect(screen.queryByText('Resolve')).not.toBeInTheDocument();
      expect(screen.queryByText('Ignore')).not.toBeInTheDocument();
    });

    it('shows action buttons for TechnicalLead role for an OPEN alert', async () => {
      renderDashboard('TechnicalLead', [sampleAlerts[0]]); // alert[0] é OPEN
      await waitFor(() => expect(screen.getByText('S3 Public Bucket')).toBeInTheDocument());
      expect(screen.getByText('Acknowledge')).toBeInTheDocument();
      expect(screen.getByText('Resolve')).toBeInTheDocument();
      expect(screen.getByText('Ignore')).toBeInTheDocument();
    });

    it('shows correct action buttons for an ACKNOWLEDGED alert for TechnicalLead', async () => {
        renderDashboard('TechnicalLead', [sampleAlerts[1]]); // alert[1] é ACKNOWLEDGED
        await waitFor(() => expect(screen.getByText('VM Public IP')).toBeInTheDocument());
        expect(screen.queryByText('Acknowledge')).not.toBeInTheDocument(); // Não deve ter Acknowledge para ACKNOWLEDGED
        expect(screen.getByText('Resolve')).toBeInTheDocument();
        expect(screen.getByText('Ignore')).toBeInTheDocument();
    });
  });

  describe('handleUpdateAlertStatus', () => {
    it('calls API to acknowledge an alert and updates UI', async () => {
      const openAlert = { ...sampleAlerts[0], status: 'OPEN', id: 3 };
      (mockAxiosInstance.patch as MockedFunction<any>).mockResolvedValueOnce({
        data: { ...openAlert, status: 'ACKNOWLEDGED', updated_at: new Date().toISOString() }
      });
      renderDashboard('TechnicalLead', [openAlert]);

      await waitFor(() => expect(screen.getByText(openAlert.title)).toBeInTheDocument());

      const ackButton = screen.getByText('Acknowledge');
      fireEvent.click(ackButton);

      await waitFor(() => {
        expect(mockAxiosInstance.patch).toHaveBeenCalledWith(
          `/alerts/${openAlert.id}/status?new_status=ACKNOWLEDGED`
        );
        // Verificar se o status do alerta mudou na UI (o botão Acknowledge some)
        expect(screen.queryByText('Acknowledge')).not.toBeInTheDocument();
        // Verificar se o texto "ACKNOWLEDGED" aparece na célula de status (precisaria de data-testid ou texto exato)
        // Por agora, a remoção do botão é um bom indicador.
      });
       expect(window.alert).toHaveBeenCalledWith(`Alert ${openAlert.id} status updated to ACKNOWLEDGED.`);
    });

    it('calls API to resolve an alert', async () => {
        const openAlert = { ...sampleAlerts[0], status: 'OPEN', id: 4 };
        (mockAxiosInstance.patch as MockedFunction<any>).mockResolvedValueOnce({
          data: { ...openAlert, status: 'RESOLVED', updated_at: new Date().toISOString() }
        });
        renderDashboard('TechnicalLead', [openAlert]);

        await waitFor(() => expect(screen.getByText(openAlert.title)).toBeInTheDocument());

        const resolveButton = screen.getByText('Resolve');
        fireEvent.click(resolveButton);

        await waitFor(() => {
          expect(mockAxiosInstance.patch).toHaveBeenCalledWith(
            `/alerts/${openAlert.id}/status?new_status=RESOLVED`
          );
        });
        expect(window.alert).toHaveBeenCalledWith(`Alert ${openAlert.id} status updated to RESOLVED.`);
      });

      it('does not call API if user does not have permission', async () => {
        const openAlert = { ...sampleAlerts[0], status: 'OPEN', id: 5 };
        renderDashboard('User', [openAlert]); // Role 'User' não tem permissão

        await waitFor(() => expect(screen.getByText(openAlert.title)).toBeInTheDocument());

        // Os botões não devem nem estar visíveis para 'User'
        expect(screen.queryByText('Acknowledge')).not.toBeInTheDocument();

        // Se tentássemos chamar handleUpdateAlertStatus diretamente (não via UI), ele deveria retornar
        // const pageInstance = screen.getByRole('main'); // Não é assim que se pega instância
        // Para testar a lógica interna de handleUpdateAlertStatus, seria um teste unitário do componente,
        // mas como estamos testando a UI, a ausência do botão já cobre o RBAC visual.
        // Se o botão estivesse lá e fosse clicado, o mock de apiClient.patch não deveria ser chamado.
        // Este teste já é coberto por 'does NOT show action buttons for User role'.
      });
  });
});
*/
