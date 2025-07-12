import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../contexts/AuthContext'; // Ajuste o caminho
import InsightsPage from './InsightsPage'; // Ajuste o caminho
import * as reportsService from '../services/reportsService'; // Para mockar as funções

// Mock dos componentes de display para simplificar o teste da InsightsPage
// e focar na lógica de busca de dados e passagem de props.
// Os componentes de display em si teriam seus próprios testes unitários (ou já têm).

jest.mock('../../components/Insights/CriticalAssetsDisplay', () => ({
  __esModule: true,
  default: ({ assets, isLoading, error }: any) => (
    <div data-testid="critical-assets-display">
      {isLoading && <p>Loading Assets...</p>}
      {error && <p>Error Assets: {error}</p>}
      {assets?.map((asset: any) => <div key={asset.id} data-testid={`asset-${asset.id}`}>{asset.name}</div>)}
    </div>
  ),
}));

jest.mock('../../components/Insights/AttackPathsDisplay', () => ({
  __esModule: true,
  default: ({ paths, isLoading, error }: any) => (
    <div data-testid="attack-paths-display">
      {isLoading && <p>Loading Paths...</p>}
      {error && <p>Error Paths: {error}</p>}
      {paths?.map((path: any) => <div key={path.id} data-testid={`path-${path.id}`}>{path.description}</div>)}
    </div>
  ),
}));

jest.mock('../../components/Insights/ProactiveRecommendationsDisplay', () => ({
  __esModule: true,
  default: ({ recommendations, isLoading, error }: any) => (
    <div data-testid="recommendations-display">
      {isLoading && <p>Loading Recommendations...</p>}
      {error && <p>Error Recommendations: {error}</p>}
      {recommendations?.map((rec: any) => <div key={rec.id} data-testid={`rec-${rec.id}`}>{rec.title}</div>)}
    </div>
  ),
}));


// Mock das funções do reportsService (ou insightsService se fosse separado)
jest.mock('../../services/reportsService', () => ({
  // Preservar outros mocks se reportsService for usado por outras páginas testadas no mesmo suite
  ...(jest.requireActual('../../services/reportsService')),
  fetchCriticalAssets: jest.fn(),
  fetchAttackPaths: jest.fn(),
  fetchProactiveRecommendations: jest.fn(),
}));

const renderInsightsPage = () => {
  const originalLocation = window.location;
  delete (window as any).location;
  window.location = { ...originalLocation, assign: jest.fn(), replace: jest.fn(), href: '' };
  localStorage.setItem('authToken', 'test-insights-token');

  return render(
    <BrowserRouter>
      <AuthProvider>
        <InsightsPage />
      </AuthProvider>
    </BrowserRouter>
  );
};

describe('InsightsPage', () => {
  const mockCriticalAssetsData = [{ id: 'ca1', name: 'Prod DB', type: 'RDS', riskScore: 90, relatedAlertsCount: 3, provider: 'AWS' }];
  const mockAttackPathsData = [{ id: 'ap1', description: 'Public VM to DB', path: [], severity: 'High' }];
  const mockRecommendationsData = [{ id: 'rec1', title: 'Enable MFA', description: 'MFA is good', category: 'IAM', severity: 'High' }];

  beforeEach(() => {
    (reportsService.fetchCriticalAssets as jest.Mock).mockResolvedValue(mockCriticalAssetsData);
    (reportsService.fetchAttackPaths as jest.Mock).mockResolvedValue(mockAttackPathsData);
    (reportsService.fetchProactiveRecommendations as jest.Mock).mockResolvedValue(mockRecommendationsData);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders the page title and section titles', async () => {
    renderInsightsPage();
    expect(screen.getByText('insightsPage.title', { exact: false })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('insightsPage.criticalAssetsTitle', { exact: false })).toBeInTheDocument();
      expect(screen.getByText('insightsPage.attackPathsTitle', { exact: false })).toBeInTheDocument();
      expect(screen.getByText('insightsPage.proactiveRecommendationsTitle', { exact: false })).toBeInTheDocument();
    });
  });

  it('calls fetch functions for each insight type on load', async () => {
    renderInsightsPage();
    await waitFor(() => {
      expect(reportsService.fetchCriticalAssets).toHaveBeenCalledTimes(1);
      expect(reportsService.fetchAttackPaths).toHaveBeenCalledTimes(1);
      expect(reportsService.fetchProactiveRecommendations).toHaveBeenCalledTimes(1);
    });
  });

  it('passes data to display components after successful fetch', async () => {
    renderInsightsPage();
    await waitFor(() => {
      expect(screen.getByTestId('asset-ca1')).toHaveTextContent('Prod DB');
      expect(screen.getByTestId('path-ap1')).toHaveTextContent('Public VM to DB');
      expect(screen.getByTestId('rec-rec1')).toHaveTextContent('Enable MFA');
    });
  });

  it('displays loading state for critical assets', async () => {
    (reportsService.fetchCriticalAssets as jest.Mock).mockImplementationOnce(() => new Promise(resolve => setTimeout(() => resolve(mockCriticalAssetsData), 50)));
    renderInsightsPage();
    expect(screen.getByText('Loading Assets...')).toBeInTheDocument(); // Do mock do componente
    await waitFor(() => expect(screen.queryByText('Loading Assets...')).not.toBeInTheDocument());
  });

  it('displays error state for critical assets if fetch fails', async () => {
    (reportsService.fetchCriticalAssets as jest.Mock).mockRejectedValueOnce(new Error('API Error Assets'));
    renderInsightsPage();
    await waitFor(() => {
      // A mensagem de erro exata depende do mock do CriticalAssetsDisplay
      // e da chave de tradução usada em InsightsPage.
      // O mock do CriticalAssetsDisplay concatena: "Error Assets: " + error
      // E a InsightsPage passa: t('insightsPage.errorCriticalAssets', 'Failed to load critical assets.')
      // Então esperamos a combinação ou parte dela.
      expect(screen.getByText(/Error Assets:.*Failed to load critical assets/i)).toBeInTheDocument();
    });
  });

  // Testes similares para loading/error de AttackPaths e ProactiveRecommendations
  it('displays loading state for attack paths', async () => {
    (reportsService.fetchAttackPaths as jest.Mock).mockImplementationOnce(() => new Promise(resolve => setTimeout(() => resolve(mockAttackPathsData), 50)));
    renderInsightsPage();
    expect(screen.getByText('Loading Paths...')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText('Loading Paths...')).not.toBeInTheDocument());
  });

  it('displays error state for attack paths if fetch fails', async () => {
    (reportsService.fetchAttackPaths as jest.Mock).mockRejectedValueOnce(new Error('API Error Paths'));
    renderInsightsPage();
    await waitFor(() => {
      expect(screen.getByText(/Error Paths:.*Failed to load attack paths/i)).toBeInTheDocument();
    });
  });

  it('displays loading state for recommendations', async () => {
    (reportsService.fetchProactiveRecommendations as jest.Mock).mockImplementationOnce(() => new Promise(resolve => setTimeout(() => resolve(mockRecommendationsData), 50)));
    renderInsightsPage();
    expect(screen.getByText('Loading Recommendations...')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText('Loading Recommendations...')).not.toBeInTheDocument());
  });

  it('displays error state for recommendations if fetch fails', async () => {
    (reportsService.fetchProactiveRecommendations as jest.Mock).mockRejectedValueOnce(new Error('API Error Recs'));
    renderInsightsPage();
    await waitFor(() => {
      expect(screen.getByText(/Error Recommendations:.*Failed to load recommendations/i)).toBeInTheDocument();
    });
  });

});
