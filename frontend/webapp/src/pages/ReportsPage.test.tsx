import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../contexts/AuthContext'; // Ajuste o caminho
import ReportsPage from './ReportsPage'; // Ajuste o caminho
import * as reportsService from '../services/reportsService'; // Para mockar as funções

// Mock do Recharts para evitar erros de renderização SVG complexos no JSDOM
// e focar na lógica da página.
jest.mock('recharts', () => {
  const OriginalRecharts = jest.requireActual('recharts');
  return {
    ...OriginalRecharts,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
    LineChart: ({ children, data }: { children: React.ReactNode, data: any[] }) => <div data-testid="line-chart" data-count={data?.length || 0}>{children}</div>,
    BarChart: ({ children, data }: { children: React.ReactNode, data: any[] }) => <div data-testid="bar-chart" data-count={data?.length || 0}>{children}</div>,
    // Mockar outros componentes do Recharts usados se necessário (XAxis, YAxis, Tooltip, etc.)
    // Por simplicidade, focaremos na existência dos gráficos principais.
    XAxis: () => <div data-testid="xaxis" />,
    YAxis: () => <div data-testid="yaxis" />,
    CartesianGrid: () => <div data-testid="cartesiangrid" />,
    Tooltip: () => <div data-testid="tooltip" />,
    Legend: () => <div data-testid="legend" />,
    Line: () => <div data-testid="line" />,
    Bar: () => <div data-testid="bar" />,
  };
});

// Mock das funções do reportsService
jest.mock('../services/reportsService', () => ({
  fetchSecurityScoreTrend: jest.fn(),
  fetchAlertsSummary: jest.fn(),
  fetchComplianceOverview: jest.fn(),
  fetchTopRisks: jest.fn(),
}));

// Helper para renderizar com providers necessários
const renderReportsPage = () => {
  // Mock para window.location
  const originalLocation = window.location;
  delete (window as any).location;
  window.location = { ...originalLocation, assign: jest.fn(), replace: jest.fn(), href: '' };

  // Simular usuário logado para AuthContext
  localStorage.setItem('authToken', 'test-reports-token');
  // Não precisamos mockar /users/me aqui pois o AuthContext já foi testado
  // e o foco é na ReportsPage. Assumimos que o usuário está logado.

  return render(
    <BrowserRouter>
      <AuthProvider> {/* AuthProvider é necessário se ReportsPage ou seus filhos usarem useAuth indiretamente */}
        <ReportsPage />
      </AuthProvider>
    </BrowserRouter>
  );
};

describe('ReportsPage', () => {
  beforeEach(() => {
    // Limpar mocks antes de cada teste
    (reportsService.fetchSecurityScoreTrend as jest.Mock).mockClear();
    (reportsService.fetchAlertsSummary as jest.Mock).mockClear();
    (reportsService.fetchComplianceOverview as jest.Mock).mockClear();
    (reportsService.fetchTopRisks as jest.Mock).mockClear();

    // Setup de dados mockados padrão para as chamadas iniciais
    (reportsService.fetchSecurityScoreTrend as jest.Mock).mockResolvedValue([
      { date: "2023-05-01", overallScore: 70, criticalAlerts: 8, highAlerts: 12 },
    ]);
    (reportsService.fetchAlertsSummary as jest.Mock).mockResolvedValue([
      { severity: "Critical", count: 15 },
    ]);
    (reportsService.fetchComplianceOverview as jest.Mock).mockResolvedValue({
      framework: "CIS Mocked", overallCompliance: 75, controls: [],
    });
    (reportsService.fetchTopRisks as jest.Mock).mockResolvedValue([
      { policyTitle: "Mocked Risk", severity: "High", instanceCount: 5, provider: "AWS" },
    ]);
  });

  it('renders the page title and initial sections', async () => {
    renderReportsPage();
    expect(screen.getByText('reportsPage.title')).toBeInTheDocument();

    // Espera que os dados sejam carregados e os títulos das seções apareçam
    await waitFor(() => {
      expect(screen.getByText('reportsPage.securityScoreTrendTitle')).toBeInTheDocument();
      expect(screen.getByText('reportsPage.alertsBySeverityTitle')).toBeInTheDocument();
      expect(screen.getByText('reportsPage.complianceOverviewTitle')).toBeInTheDocument();
      expect(screen.getByText('reportsPage.topRisksTitle')).toBeInTheDocument();
    });
  });

  it('calls fetch functions on initial load with default filters', async () => {
    renderReportsPage();
    await waitFor(() => {
      expect(reportsService.fetchSecurityScoreTrend).toHaveBeenCalledWith({
        period: 'weekly', // Default period
        provider: undefined,
      });
      expect(reportsService.fetchAlertsSummary).toHaveBeenCalledWith({
        group_by: 'severity',
        period: 'weekly',
        provider: undefined,
      });
      expect(reportsService.fetchComplianceOverview).toHaveBeenCalledWith({
        provider: undefined,
      });
      expect(reportsService.fetchTopRisks).toHaveBeenCalledWith({
        provider: undefined,
        limit: 10,
      });
    });
  });

  it('renders charts after data is loaded', async () => {
    renderReportsPage();
    await waitFor(() => {
      // Verifica se os componentes mockados do Recharts estão presentes
      expect(screen.getAllByTestId('responsive-container').length).toBeGreaterThanOrEqual(2); // Pelo menos para Trend e Severity
      expect(screen.getAllByTestId('line-chart').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByTestId('bar-chart').length).toBeGreaterThanOrEqual(1);
      // Verifica se os gráficos receberam dados (baseado no data-count do mock)
      expect(screen.getAllByTestId('line-chart')[0]).toHaveAttribute('data-count', '1');
      expect(screen.getAllByTestId('bar-chart')[0]).toHaveAttribute('data-count', '1');
    });
  });

  it('refetches data when period filter changes', async () => {
    renderReportsPage();
    await waitFor(() => expect(reportsService.fetchSecurityScoreTrend).toHaveBeenCalledTimes(1));

    const periodSelect = screen.getByLabelText('reportsPage.filterLabelPeriod');
    await act(async () => {
      userEvent.selectOptions(periodSelect, 'monthly');
    });

    await waitFor(() => {
      expect(reportsService.fetchSecurityScoreTrend).toHaveBeenCalledTimes(2);
      expect(reportsService.fetchSecurityScoreTrend).toHaveBeenCalledWith(expect.objectContaining({ period: 'monthly' }));
      // Verificar outras chamadas de fetch se elas também usarem o filtro de período
      expect(reportsService.fetchAlertsSummary).toHaveBeenCalledWith(expect.objectContaining({ period: 'monthly' }));
    });
  });

  it('refetches data when provider filter changes', async () => {
    renderReportsPage();
    await waitFor(() => expect(reportsService.fetchSecurityScoreTrend).toHaveBeenCalledTimes(1));

    const providerSelect = screen.getByLabelText('reportsPage.filterLabelProvider');
    await act(async () => {
      userEvent.selectOptions(providerSelect, 'AWS');
    });

    await waitFor(() => {
      expect(reportsService.fetchSecurityScoreTrend).toHaveBeenCalledTimes(2);
      expect(reportsService.fetchSecurityScoreTrend).toHaveBeenCalledWith(expect.objectContaining({ provider: 'AWS' }));
      expect(reportsService.fetchComplianceOverview).toHaveBeenCalledWith(expect.objectContaining({ provider: 'AWS' }));
      expect(reportsService.fetchTopRisks).toHaveBeenCalledWith(expect.objectContaining({ provider: 'AWS' }));
    });
  });

  it('displays loading messages while data is being fetched', async () => {
    // Modificar mocks para introduzir um delay maior ou estado de pending
    (reportsService.fetchSecurityScoreTrend as jest.Mock).mockImplementationOnce(() => new Promise(resolve => setTimeout(() => resolve([]), 100)));

    renderReportsPage();

    // Imediatamente após render, loading message deve estar visível para Trend
    // (Outras podem já ter resolvido se o mock for rápido)
    expect(screen.getAllByText('reportsPage.loadingData').length).toBeGreaterThanOrEqual(1);

    await waitFor(() => {
      // Após o delay, a mensagem de loading para Trend deve sumir
      // E se os dados forem vazios, "noDataAvailable" aparece
      expect(screen.queryByText('reportsPage.loadingData')).not.toBeInTheDocument();
      // Ou verificar se o gráfico está renderizado
    });
  });

  it('displays error messages if fetching data fails', async () => {
    (reportsService.fetchSecurityScoreTrend as jest.Mock).mockRejectedValueOnce(new Error('Trend API Error'));

    renderReportsPage();

    await waitFor(() => {
      expect(screen.getByText('reportsPage.errorFetchingTrend')).toBeInTheDocument();
    });
  });

});
