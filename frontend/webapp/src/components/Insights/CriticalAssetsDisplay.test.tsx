import React from 'react';
import { render, screen } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import CriticalAssetsDisplay from './CriticalAssetsDisplay'; // Ajuste o caminho
import { CriticalAsset } from '../../services/reportsService'; // Ajuste o caminho

// Mock de i18next já está em setupTests.ts

const mockAssets: CriticalAsset[] = [
  { id: 'asset-001', name: 'Prod DB Server', type: 'RDS Instance', riskScore: 95, relatedAlertsCount: 5, provider: 'AWS' },
  { id: 'asset-002', name: 'Main K8s Cluster', type: 'EKS Cluster', riskScore: 80, relatedAlertsCount: 3, provider: 'AWS' },
  { id: 'asset-003', name: 'Billing Storage', type: 'S3 Bucket', riskScore: 70, relatedAlertsCount: 7, provider: 'GCP' },
];

const renderWithMantine = (ui: React.ReactElement) => {
  return render(<MantineProvider>{ui}</MantineProvider>);
};

describe('CriticalAssetsDisplay Component', () => {
  it('renders loading message when isLoading is true', () => {
    renderWithMantine(<CriticalAssetsDisplay assets={[]} isLoading={true} error={null} />);
    expect(screen.getByText('insightsPage.loadingCriticalAssets', { exact: false })).toBeInTheDocument();
  });

  it('renders error message when error is present', () => {
    renderWithMantine(<CriticalAssetsDisplay assets={[]} isLoading={false} error="Failed to fetch" />);
    expect(screen.getByText(/Error loading critical assets: Failed to fetch/i)).toBeInTheDocument();
  });

  it('renders "no assets" message when assets array is empty and not loading', () => {
    renderWithMantine(<CriticalAssetsDisplay assets={[]} isLoading={false} error={null} />);
    expect(screen.getByText('insightsPage.noCriticalAssets', { exact: false })).toBeInTheDocument();
  });

  it('renders a list of critical assets correctly', () => {
    renderWithMantine(<CriticalAssetsDisplay assets={mockAssets} isLoading={false} error={null} />);

    expect(screen.getByText('Prod DB Server (RDS Instance - AWS)')).toBeInTheDocument();
    expect(screen.getByText((content, element) => content.startsWith('insightsPage.assetId') && content.includes('asset-001'))).toBeInTheDocument();
    expect(screen.getByText((content, element) => content.startsWith('insightsPage.riskScore') && content.includes('95'))).toBeInTheDocument();
    expect(screen.getByText((content, element) => content.startsWith('insightsPage.relatedAlerts') && content.includes('5'))).toBeInTheDocument();

    expect(screen.getByText('Main K8s Cluster (EKS Cluster - AWS)')).toBeInTheDocument();
    expect(screen.getByText((content, element) => content.startsWith('insightsPage.assetId') && content.includes('asset-002'))).toBeInTheDocument();
    expect(screen.getByText((content, element) => content.startsWith('insightsPage.riskScore') && content.includes('80'))).toBeInTheDocument();

    expect(screen.getByText('Billing Storage (S3 Bucket - GCP)')).toBeInTheDocument();
    expect(screen.getByText((content, element) => content.startsWith('insightsPage.riskScore') && content.includes('70'))).toBeInTheDocument();
  });

  it('applies correct color styling for risk scores', () => {
    renderWithMantine(<CriticalAssetsDisplay assets={mockAssets} isLoading={false} error={null} />);

    // Asset 1: Risk Score 95 (espera cor vermelha)
    const riskScore95 = screen.getByText('95');
    expect(riskScore95).toHaveStyle('color: var(--mantine-color-red-filled)'); // ou a cor exata se não for do tema

    // Asset 2: Risk Score 80 (espera cor laranja)
    const riskScore80 = screen.getByText('80');
    expect(riskScore80).toHaveStyle('color: var(--mantine-color-orange-filled)'); // ou a cor exata

    // Asset 3: Risk Score 70 (espera cor dimmed/padrão)
    const riskScore70 = screen.getByText('70');
    expect(riskScore70).toHaveStyle('color: var(--mantine-color-dimmed)'); // ou a cor exata
  });
});
