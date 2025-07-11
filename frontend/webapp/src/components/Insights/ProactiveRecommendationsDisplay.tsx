import React from 'react';
import { useTranslation } from 'react-i18next';
import { ProactiveRecommendation } from '../../services/reportsService'; // Ajuste o caminho se necessário
import { Paper, Title, Text, Badge } from '@mantine/core'; // Importar da Mantine

interface ProactiveRecommendationsDisplayProps {
  recommendations: ProactiveRecommendation[];
  isLoading: boolean;
  error: string | null;
}

const ProactiveRecommendationsDisplay: React.FC<ProactiveRecommendationsDisplayProps> = ({ recommendations, isLoading, error }) => {
  const { t } = useTranslation();

  if (isLoading) {
    return <Text>{t('insightsPage.loadingRecommendations', 'Loading proactive recommendations...')}</Text>;
  }

  if (error) {
    return <Text c="red">{t('insightsPage.errorRecommendations', 'Error loading recommendations:')} {error}</Text>;
  }

  if (!recommendations || recommendations.length === 0) {
    return <Text>{t('insightsPage.noRecommendations', 'No proactive recommendations available at the moment.')}</Text>;
  }

  const getSeverityBadgeColor = (severity: 'High' | 'Medium' | 'Low'): string => {
    switch (severity) {
      case 'High': return 'red';
      case 'Medium': return 'yellow';
      case 'Low': return 'blue';
      default: return 'gray';
    }
  };

  return (
    <div>
      {recommendations.map(rec => (
        <Paper key={rec.id} p="lg" shadow="xs" radius="md" withBorder mb="md">
          <Title order={4} mb="sm">
            {rec.title}
          </Title>
          <Group gap="xs" mb="xs">
            <Text size="xs" c="dimmed">{t('insightsPage.recommendationCategory', 'Category:')} {rec.category}</Text>
            <Badge color={getSeverityBadgeColor(rec.severity)} variant="light" size="sm">
              {rec.severity}
            </Badge>
          </Group>
          <Text size="sm">{rec.description}</Text>
        </Paper>
      ))}
    </div>
  );
};

export default ProactiveRecommendationsDisplay;
