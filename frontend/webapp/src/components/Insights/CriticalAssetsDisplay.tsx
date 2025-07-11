import React from 'react';
import { useTranslation } from 'react-i18next';
import { CriticalAsset } from '../../services/reportsService'; // Ajuste o caminho se necessário

// Reutilizar simulação de Paper e Title ou importar de um local comum
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


interface CriticalAssetsDisplayProps {
  assets: CriticalAsset[];
  isLoading: boolean;
  error: string | null;
}

const CriticalAssetsDisplay: React.FC<CriticalAssetsDisplayProps> = ({ assets, isLoading, error }) => {
  const { t } = useTranslation();

  if (isLoading) {
    return <p>{t('insightsPage.loadingCriticalAssets', 'Loading critical assets...')}</p>;
  }

  if (error) {
    return <p style={{ color: 'red' }}>{t('insightsPage.errorCriticalAssets', 'Error loading critical assets:')} {error}</p>;
  }

  if (!assets || assets.length === 0) {
    return <p>{t('insightsPage.noCriticalAssets', 'No critical assets identified at the moment.')}</p>;
  }

  return (
    <div>
      {assets.map(asset => (
        <Paper key={asset.id} padding="lg" shadow="xs" style={{ marginBottom: '15px' }}>
          <Title order={4} style={{ marginBottom: '10px' }}>
            {asset.name} ({asset.type} - {asset.provider})
          </Title>
          <p><strong>{t('insightsPage.assetId', 'Asset ID:')}</strong> {asset.id}</p>
          <p><strong>{t('insightsPage.riskScore', 'Risk Score:')}</strong> <span style={{color: asset.riskScore > 90 ? 'red' : (asset.riskScore > 75 ? 'orange' : 'inherit')}}>{asset.riskScore}</span></p>
          <p><strong>{t('insightsPage.relatedAlerts', 'Related Alerts:')}</strong> {asset.relatedAlertsCount}</p>
        </Paper>
      ))}
    </div>
  );
};

export default CriticalAssetsDisplay;
