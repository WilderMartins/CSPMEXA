import React from 'react';
import { useTranslation } from 'react-i18next';
import { AttackPath } from '../../services/reportsService'; // Ajuste o caminho se necessário
import { Paper, Title, Text, List } from '@mantine/core'; // Importar da Mantine

interface AttackPathsDisplayProps {
  paths: AttackPath[];
  isLoading: boolean;
  error: string | null;
}

const AttackPathsDisplay: React.FC<AttackPathsDisplayProps> = ({ paths, isLoading, error }) => {
  const { t } = useTranslation();

  if (isLoading) {
    return <Text>{t('insightsPage.loadingAttackPaths', 'Loading potential attack paths...')}</Text>;
  }

  if (error) {
    return <Text c="red">{t('insightsPage.errorAttackPaths', 'Error loading attack paths:')} {error}</Text>;
  }

  if (!paths || paths.length === 0) {
    return <Text>{t('insightsPage.noAttackPaths', 'No potential attack paths identified at the moment.')}</Text>;
  }

  const getSeverityColor = (severity: 'High' | 'Medium' | 'Low'): string => {
    if (severity === 'High') return 'var(--mantine-color-red-7)';
    if (severity === 'Medium') return 'var(--mantine-color-orange-7)';
    return 'var(--mantine-color-yellow-7)'; // Ajustar se necessário para contraste
  };

  return (
    <div>
      {paths.map(path => (
        <Paper key={path.id} p="lg" shadow="xs" radius="md" withBorder mb="md">
          <Title order={4} mb="sm">
            {t('insightsPage.attackPathId', 'Path ID:')} {path.id} -
            <Text component="span" c={getSeverityColor(path.severity)} fw={500}> {path.severity}</Text>
          </Title>
          <Text size="sm" mb="xs"><strong>{t('insightsPage.attackPathDescription', 'Description:')}</strong> {path.description}</Text>
          <div>
            <Text size="sm" fw={500} mb="xs">{t('insightsPage.pathSegments', 'Segments:')}</Text>
            <List type="ordered" size="sm" withPadding>
              {path.path.map((segment, index) => (
                <List.Item key={index}>
                  <Text component="span" fz="sm"><em>{segment.resourceType} ({segment.resourceId})</em>: {segment.vulnerability}</Text>
                </List.Item>
              ))}
            </List>
          </div>
        </Paper>
      ))}
    </div>
  );
};

export default AttackPathsDisplay;
