import React from 'react';
import { useTranslation } from 'react-i18next';
import { ProactiveRecommendation } from '../../services/reportsService'; // Ajuste o caminho se necessário

// Reutilizar simulação de Paper e Title
const Paper: React.FC<{ children: React.ReactNode, padding?: string | number, shadow?: string, style?: React.CSSProperties }> = ({ children, style, padding = 'md', shadow = 'sm', ...props }) => (
  <div
    style={{
      padding: typeof padding === 'number' ? `${padding}px` : padding,
      boxShadow: shadow === 'sm' ? `0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.1)` : 'none',
      border: '1px solid #e0e0e0',
      borderRadius: '5px',
      marginBottom: '20px',
      ...style
    }}
    {...props}
  >
    {children}
  </div>
);

const Title: React.FC<{ order?: 1 | 2 | 3 | 4 | 5 | 6, children: React.ReactNode, style?: React.CSSProperties }> = ({ order = 3, children, style }) => {
  const Tag = `h${order}` as keyof JSX.IntrinsicElements;
  return <Tag style={{ marginTop: 0, marginBottom: '1rem', fontWeight: 600, ...style }}>{children}</Tag>;
};

interface ProactiveRecommendationsDisplayProps {
  recommendations: ProactiveRecommendation[];
  isLoading: boolean;
  error: string | null;
}

const ProactiveRecommendationsDisplay: React.FC<ProactiveRecommendationsDisplayProps> = ({ recommendations, isLoading, error }) => {
  const { t } = useTranslation();

  if (isLoading) {
    return <p>{t('insightsPage.loadingRecommendations', 'Loading proactive recommendations...')}</p>;
  }

  if (error) {
    return <p style={{ color: 'red' }}>{t('insightsPage.errorRecommendations', 'Error loading recommendations:')} {error}</p>;
  }

  if (!recommendations || recommendations.length === 0) {
    return <p>{t('insightsPage.noRecommendations', 'No proactive recommendations available at the moment.')}</p>;
  }

  const getSeverityStyle = (severity: 'High' | 'Medium' | 'Low'): React.CSSProperties => {
    let color = '#212529'; // Default text color
    let fontWeight: 'normal' | 'bold' = 'normal';

    switch (severity) {
      case 'High': // Assuming 'Critical' might be used interchangeably or a specific 'Critical' style is needed
        color = '#dc3545'; // Vermelho Bootstrap
        fontWeight = 'bold';
        break;
      case 'Medium':
        color = '#ffc107'; // Amarelo Bootstrap
        break;
      case 'Low':
        color = '#17a2b8'; // Info Bootstrap (ciano)
        break;
    }
    return { color, fontWeight, display: 'inline-block', padding: '2px 6px', borderRadius: '4px', border: `1px solid ${color}`, fontSize: '0.85em' };
  };


  return (
    <div>
      {recommendations.map(rec => (
        <Paper key={rec.id} padding="lg" shadow="xs" style={{ marginBottom: '15px' }}>
          <Title order={4} style={{ marginBottom: '10px' }}>
            {rec.title}
          </Title>
          <p style={{fontSize: '0.9em', color: '#555'}}>
            <strong>{t('insightsPage.recommendationCategory', 'Category:')}</strong> {rec.category} | <strong>{t('insightsPage.recommendationSeverity', 'Severity:')}</strong> <span style={getSeverityStyle(rec.severity)}>{rec.severity}</span>
          </p>
          <p>{rec.description}</p>
        </Paper>
      ))}
    </div>
  );
};

export default ProactiveRecommendationsDisplay;
