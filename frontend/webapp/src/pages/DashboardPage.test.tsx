import React from 'react';
import { render, screen, act, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { BrowserRouter } from 'react-router-dom'; // Necessário por causa de <Link> ou <Navigate> em componentes filhos ou no próprio AuthContext
import { AuthProvider } from '../contexts/AuthContext'; // Ajuste o caminho se necessário
import DashboardPage from './DashboardPage'; // Ajuste o caminho se necessário
import { Alert } from '../components/Dashboard/AlertsTable'; // Importar a interface Alert

const mockApi = new MockAdapter(axios);

// Mock do ProviderAnalysisSection para simplificar os testes do DashboardPage
jest.mock('../components/Dashboard/ProviderAnalysisSection', () => ({
  __esModule: true,
  default: ({ providerId, inputFields, analysisButtons, onAnalyze, isLoading, currentAnalysisType }: any) => (
    <div data-testid={`provider-section-${providerId}`}>
      {inputFields?.map((field: any) => (
        <div key={field.id}>
          <label htmlFor={field.id}>{field.labelKey}</label>
          <input
            id={field.id}
            data-testid={`${providerId}-${field.id}-input`}
            value={field.value}
            onChange={(e) => field.setter(e.target.value)}
            placeholder={field.placeholderKey}
          />
        </div>
      ))}
      {analysisButtons?.map((button: any) => (
        <button
          key={button.id}
          data-testid={`${providerId}-${button.id}-button`}
          onClick={() => onAnalyze(providerId, button.servicePath, button.analysisType,
            inputFields?.reduce((acc: any, cur: any) => { acc[cur.id] = cur.value; return acc; }, {}))}
          disabled={isLoading}
        >
          {isLoading && currentAnalysisType === button.analysisType ? 'dashboardPage.analyzingButton' : button.labelKey}
        </button>
      ))}
    </div>
  ),
}));

// Mock do AlertsTable para focar nos testes do DashboardPage
const mockAlertsTableData: Alert[] = [];
jest.mock('../components/Dashboard/AlertsTable', () => ({
  __esModule: true,
  default: ({ alerts, title }: { alerts: Alert[], title: string }) => (
    <div data-testid="alerts-table">
      <h3 data-testid="alerts-table-title">{title}</h3>
      {alerts.map(alert => <div key={alert.id} data-testid={`alert-item-${alert.id}`}>{alert.title}</div>)}
      <span data-testid="alerts-count">{alerts.length}</span>
    </div>
  ),
  // Exportar a interface Alert se ela for definida aqui e usada pelo DashboardPage
  // Se Alert é importada de outro lugar no original, mantenha essa importação.
}));


const renderDashboardWithAuthProvider = () => {
  // Mock para window.location, pois o AuthContext pode tentar redirecionar
  const originalLocation = window.location;
  delete (window as any).location;
  window.location = { ...originalLocation, assign: jest.fn(), replace: jest.fn(), href: '' };

  // Simula um usuário logado
  localStorage.setItem('authToken', 'test-dashboard-token');
  mockApi.onGet('/api/v1/users/me').reply(200, { user_id: 'dash-user', email: 'dash@example.com' });

  const utils = render(
    <BrowserRouter>
      <AuthProvider>
        <DashboardPage />
      </AuthProvider>
    </BrowserRouter>
  );

  // Restaurar window.location após o setup do render
  // window.location = originalLocation; // Isso pode ser problemático se o componente desmontar/remontar
  return utils;
};


describe('DashboardPage', () => {
  beforeEach(() => {
    localStorage.clear();
    mockApi.reset();
  });

  it('renders initial user info and fetches initial alerts', async () => {
    const initialAlerts: Alert[] = [
      { id: 100, title: 'Initial Alert 1', provider: 'AWS', severity: 'High', status: 'Open', resource_id: 'res1', resource_type: 's3', policy_id: 'p1', description: '', created_at: '', updated_at: '', first_seen_at: '', last_seen_at: '' },
    ];
    mockApi.onGet('/api/v1/alerts?limit=100&sort_by=last_seen_at&sort_order=desc').reply(200, initialAlerts);

    renderDashboardWithAuthProvider();

    // Verifica informações do usuário (mockado em AuthProvider)
    expect(await screen.findByText('dashboardPage.welcomeMessage', { userId: 'dash-user' })).toBeInTheDocument();

    // Verifica se a tabela de alertas foi renderizada com o título correto e os alertas iniciais
    await waitFor(() => {
      expect(screen.getByTestId('alerts-table-title')).toHaveTextContent('dashboardPage.allPersistedAlerts');
    });
    expect(screen.getByTestId('alert-item-100')).toHaveTextContent('Initial Alert 1');
    expect(screen.getByTestId('alerts-count')).toHaveTextContent(initialAlerts.length.toString());
  });

  it('allows typing into provider ID fields (e.g., GCP Project ID)', async () => {
    mockApi.onGet('/api/v1/alerts?limit=100&sort_by=last_seen_at&sort_order=desc').reply(200, []); // Sem alertas iniciais
    renderDashboardWithAuthProvider();
    await screen.findByText('dashboardPage.welcomeMessage', { userId: 'dash-user' }); // Espera a página carregar

    // Simula a navegação para a aba GCP (o mock do ProviderAnalysisSection não tem abas reais, então testamos o input diretamente)
    // Em um teste mais complexo com Tabs reais, você clicaria na aba primeiro.
    const gcpTabButton = screen.getByRole('button', { name: 'GCP' }); // Supondo que o TabPanel tenha um 'label' que vira o nome do botão
    userEvent.click(gcpTabButton);

    const gcpProjectIdInput = screen.getByTestId('gcp-projectId-input') as HTMLInputElement;
    await userEvent.type(gcpProjectIdInput, 'test-gcp-project');
    expect(gcpProjectIdInput.value).toBe('test-gcp-project');
  });

  it('triggers analysis and updates alerts table on analysis button click', async () => {
    mockApi.onGet('/api/v1/alerts?limit=100&sort_by=last_seen_at&sort_order=desc').reply(200, []); // Sem alertas iniciais

    const analysisAlerts: Alert[] = [
      { id: 200, title: 'GCP Analysis Alert', provider: 'GCP', severity: 'Medium', status: 'Open', resource_id: 'res2', resource_type: 'vm', policy_id: 'p2', description: '', created_at: '', updated_at: '', first_seen_at: '', last_seen_at: '' },
    ];
    // Mock para a chamada de análise GCP Storage
    mockApi.onPost('/api/v1/analyze/gcp/storage/buckets?project_id=my-gcp-project').reply(200, analysisAlerts);

    renderDashboardWithAuthProvider();
    await screen.findByText('dashboardPage.welcomeMessage', { userId: 'dash-user' });

    // Simula a navegação para a aba GCP e preenchimento do ID
    const gcpTabButton = screen.getByRole('button', { name: 'GCP' });
    userEvent.click(gcpTabButton);
    const gcpProjectIdInput = screen.getByTestId('gcp-projectId-input') as HTMLInputElement;
    await userEvent.type(gcpProjectIdInput, 'my-gcp-project');

    // Clica no botão de análise (usando o data-testid do mock do ProviderAnalysisSection)
    // O ID do botão de análise GCP Storage é 'storage' na config do DashboardPage
    const analyzeGcpStorageButton = screen.getByTestId('gcp-storage-button');

    await act(async () => {
        userEvent.click(analyzeGcpStorageButton);
    });

    // Verifica se a tabela de alertas é atualizada
    await waitFor(() => {
      expect(screen.getByTestId('alerts-table-title')).toHaveTextContent('dashboardPage.alertsFoundFor', {type: 'GCP Storage Buckets'});
    });
    expect(screen.getByTestId('alert-item-200')).toHaveTextContent('GCP Analysis Alert');
    expect(screen.getByTestId('alerts-count')).toHaveTextContent(analysisAlerts.length.toString());

    // Verifica se a chamada POST foi feita
    expect(mockApi.history.post.length).toBe(1);
    expect(mockApi.history.post[0].url).toBe('/api/v1/analyze/gcp/storage/buckets?project_id=my-gcp-project');
  });

  it('refetches all alerts when "Fetch All Alerts" button is clicked', async () => {
    mockApi.onGet('/api/v1/alerts?limit=100&sort_by=last_seen_at&sort_order=desc')
        .replyOnce(200, [{ id: 1, title: 'First Load Alert', provider: 'AWS', severity: 'Low', status:'Open', resource_id: 'r1', resource_type:'t1', policy_id:'p1',description:'',created_at:'',updated_at:'',first_seen_at:'',last_seen_at:'' }]) // Primeira carga
        .replyOnce(200, [{ id: 2, title: 'Refreshed Alert', provider: 'AWS', severity: 'Low', status:'Open', resource_id: 'r2', resource_type:'t2', policy_id:'p2',description:'',created_at:'',updated_at:'',first_seen_at:'',last_seen_at:'' }]); // Carga após clique

    renderDashboardWithAuthProvider();

    // Espera pela primeira carga
    await screen.findByTestId('alert-item-1');
    expect(screen.getByTestId('alert-item-1')).toHaveTextContent('First Load Alert');
    expect(screen.queryByTestId('alert-item-2')).not.toBeInTheDocument();

    const fetchAllButton = screen.getByText('dashboardPage.fetchAllAlertsButton');

    await act(async () => {
      userEvent.click(fetchAllButton);
    });

    // Espera pela segunda carga (após clique)
    await screen.findByTestId('alert-item-2');
    expect(screen.getByTestId('alert-item-2')).toHaveTextContent('Refreshed Alert');
    expect(screen.queryByTestId('alert-item-1')).not.toBeInTheDocument(); // A tabela é limpa e repopulada
    expect(screen.getByTestId('alerts-table-title')).toHaveTextContent('dashboardPage.allPersistedAlerts');

    expect(mockApi.history.get.filter(req => req.url?.includes('/api/v1/alerts')).length).toBe(3); // 1 users/me + 2 alerts
  });

});
