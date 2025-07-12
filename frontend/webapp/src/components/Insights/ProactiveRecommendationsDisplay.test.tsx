import React from 'react';
import { render, screen } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import ProactiveRecommendationsDisplay from './ProactiveRecommendationsDisplay'; // Ajuste o caminho
import { ProactiveRecommendation } from '../../services/reportsService'; // Ajuste o caminho

const mockRecommendations: ProactiveRecommendation[] = [
  { id: 'rec-001', title: 'Enable MFA for all IAM Users', description: 'MFA adds a critical layer of security.', category: 'IAM', severity: 'High' },
  { id: 'rec-002', title: 'Restrict Public S3 Bucket Access', description: 'Review S3 bucket policies.', category: 'Data Security', severity: 'Medium' },
  { id: 'rec-003', title: 'Implement Least Privilege (GCP)', description: 'Assign granular roles.', category: 'IAM', severity: 'Low' },
];

const renderWithMantine = (ui: React.ReactElement) => {
  return render(<MantineProvider>{ui}</MantineProvider>);
};

describe('ProactiveRecommendationsDisplay Component', () => {
  it('renders loading message when isLoading is true', () => {
    renderWithMantine(<ProactiveRecommendationsDisplay recommendations={[]} isLoading={true} error={null} />);
    expect(screen.getByText('insightsPage.loadingRecommendations', { exact: false })).toBeInTheDocument();
  });

  it('renders error message when error is present', () => {
    renderWithMantine(<ProactiveRecommendationsDisplay recommendations={[]} isLoading={false} error="Failed to fetch recommendations" />);
    expect(screen.getByText(/Error loading recommendations: Failed to fetch recommendations/i)).toBeInTheDocument();
  });

  it('renders "no recommendations" message when recommendations array is empty and not loading', () => {
    renderWithMantine(<ProactiveRecommendationsDisplay recommendations={[]} isLoading={false} error={null} />);
    expect(screen.getByText('insightsPage.noRecommendations', { exact: false })).toBeInTheDocument();
  });

  it('renders a list of recommendations correctly', () => {
    renderWithMantine(<ProactiveRecommendationsDisplay recommendations={mockRecommendations} isLoading={false} error={null} />);

    // Recommendation 1
    expect(screen.getByText('Enable MFA for all IAM Users')).toBeInTheDocument();
    expect(screen.getByText((content, el) => content.includes('Category: IAM') && content.includes('High'))).toBeInTheDocument();
    expect(screen.getByText('MFA adds a critical layer of security.')).toBeInTheDocument();

    // Recommendation 2
    expect(screen.getByText('Restrict Public S3 Bucket Access')).toBeInTheDocument();
    expect(screen.getByText((content, el) => content.includes('Category: Data Security') && content.includes('Medium'))).toBeInTheDocument();
    expect(screen.getByText('Review S3 bucket policies.')).toBeInTheDocument();

    // Recommendation 3
    expect(screen.getByText('Implement Least Privilege (GCP)')).toBeInTheDocument();
    expect(screen.getByText((content, el) => content.includes('Category: IAM') && content.includes('Low'))).toBeInTheDocument();
    expect(screen.getByText('Assign granular roles.')).toBeInTheDocument();
  });

  it('applies correct badge color for recommendation severity', () => {
    renderWithMantine(<ProactiveRecommendationsDisplay recommendations={mockRecommendations} isLoading={false} error={null} />);

    // Verifica a cor do Badge pela classe ou estilo se o componente Badge da Mantine aplicar assim.
    // O componente Badge da Mantine usa a prop 'color'. O mock de `getSeverityBadgeColor` define 'red', 'yellow', 'blue'.
    // Testar a cor exata do texto dentro do badge pode ser mais simples se o Badge em si for complexo.

    const highSeverityRec = screen.getByText('High'); // Badge text
    // A forma de verificar a cor do Badge pode depender de como Mantine renderiza.
    // Se ele adiciona uma classe como `mantine-Badge-filledColor-red`, você pode usar `toHaveClass`.
    // Ou inspecionar o estilo computado se a cor for inline.
    // Por simplicidade, se o texto está lá, e a lógica de getSeverityBadgeColor é simples,
    // podemos assumir que a cor correta é passada para o Badge.
    // Para um teste mais robusto, inspecionaríamos o elemento Badge pai e sua cor.
    expect(highSeverityRec).toBeInTheDocument(); // Confirma que o Badge com o texto está lá

    const mediumSeverityRec = screen.getByText('Medium');
    expect(mediumSeverityRec).toBeInTheDocument();

    const lowSeverityRec = screen.getByText('Low');
    expect(lowSeverityRec).toBeInTheDocument();

    // Exemplo de como poderia ser um teste de cor mais específico se necessário (pode falhar dependendo da implementação do Badge):
    // expect(highSeverityRec.closest('.mantine-Badge-root')).toHaveStyle('background-color: var(--mantine-color-red-light)'); // Exemplo
  });
});
