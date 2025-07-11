import React from 'react';
import { useTranslation } from 'react-i18next';
import { AttackPath } from '../../services/reportsService'; // Ajuste o caminho se necessário

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

interface AttackPathsDisplayProps {
  paths: AttackPath[];
  isLoading: boolean;
  error: string | null;
}

const AttackPathsDisplay: React.FC<AttackPathsDisplayProps> = ({ paths, isLoading, error }) => {
  const { t } = useTranslation();

  if (isLoading) {
    return <p>{t('insightsPage.loadingAttackPaths', 'Loading potential attack paths...')}</p>;
  }

  if (error) {
    return <p style={{ color: 'red' }}>{t('insightsPage.errorAttackPaths', 'Error loading attack paths:')} {error}</p>;
  }

  if (!paths || paths.length === 0) {
    return <p>{t('insightsPage.noAttackPaths', 'No potential attack paths identified at the moment.')}</p>;
  }

  const getSeverityColor = (severity: 'High' | 'Medium' | 'Low') => {
    if (severity === 'High') return 'red';
    if (severity === 'Medium') return 'orange';
    return '#DAA520'; // Default for Low or other
  };

  return (
    <div>
      {paths.map(path => (
        <Paper key={path.id} padding="lg" shadow="xs" style={{ marginBottom: '15px' }}>
          <Title order={4} style={{ marginBottom: '10px' }}>
            {t('insightsPage.attackPathId', 'Path ID:')} {path.id} - <span style={{color: getSeverityColor(path.severity)}}>{path.severity}</span>
          </Title>
          <p><strong>{t('insightsPage.attackPathDescription', 'Description:')}</strong> {path.description}</p>
          <div>
            <strong>{t('insightsPage.pathSegments', 'Segments:')}</strong>
            <ul style={{ listStyleType: 'decimal', paddingLeft: '20px', marginTop: '5px' }}>
              {path.path.map((segment, index) => (
                <li key={index} style={{ marginBottom: '5px' }}>
                  <em>{segment.resourceType} ({segment.resourceId})</em>: {segment.vulnerability}
                </li>
              ))}
            </ul>
          </div>
        </Paper>
      ))}
    </div>
  );
};

export default AttackPathsDisplay;
