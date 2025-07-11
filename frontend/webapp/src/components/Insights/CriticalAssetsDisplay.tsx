import React from 'react';
import { useTranslation } from 'react-i18next';
import { CriticalAsset } from '../../services/reportsService'; // Ajuste o caminho se necessário
import { Paper, Title, Text } from '@mantine/core'; // Importar da Mantine

interface CriticalAssetsDisplayProps {
  assets: CriticalAsset[];
  isLoading: boolean;
  error: string | null;
}

const CriticalAssetsDisplay: React.FC<CriticalAssetsDisplayProps> = ({ assets, isLoading, error }) => {
  const { t } = useTranslation();

  if (isLoading) {
    return <Text>{t('insightsPage.loadingCriticalAssets', 'Loading critical assets...')}</Text>;
  }

  if (error) {
    return <Text c="red">{t('insightsPage.errorCriticalAssets', 'Error loading critical assets:')} {error}</Text>;
  }

  if (!assets || assets.length === 0) {
    return <Text>{t('insightsPage.noCriticalAssets', 'No critical assets identified at the moment.')}</Text>;
  }

  return (
    <div>
      {assets.map(asset => (
        <Paper key={asset.id} p="lg" shadow="xs" radius="md" withBorder mb="md">
          <Title order={4} mb="sm">
            {asset.name} ({asset.type} - {asset.provider})
          </Title>
          <Text size="sm"><strong>{t('insightsPage.assetId', 'Asset ID:')}</strong> {asset.id}</Text>
          <Text size="sm">
            <strong>{t('insightsPage.riskScore', 'Risk Score:')}</strong>
            <Text component="span" c={asset.riskScore > 90 ? 'red' : (asset.riskScore > 75 ? 'orange' : 'dimmed')} fw={500}> {asset.riskScore}</Text>
          </Text>
          <Text size="sm"><strong>{t('insightsPage.relatedAlerts', 'Related Alerts:')}</strong> {asset.relatedAlertsCount}</Text>
        </Paper>
      ))}
    </div>
  );
};

export default CriticalAssetsDisplay;
