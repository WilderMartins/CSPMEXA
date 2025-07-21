import React from 'react';
import { useTranslation } from 'react-i18next';
import { Paper, Text, Title, Group, Badge } from '@mantine/core';
import { Link } from 'react-router-dom';

interface ProviderSummary {
  provider: string;
  total_alerts: number;
  by_severity: { [key: string]: number };
}

interface ProviderSummaryCardProps {
  summary: ProviderSummary;
}

const severityColors: { [key: string]: string } = {
  CRITICAL: 'red',
  HIGH: 'orange',
  MEDIUM: 'yellow',
  LOW: 'blue',
  INFO: 'cyan'
};

const ProviderSummaryCard: React.FC<ProviderSummaryCardProps> = ({ summary }) => {
  const { t } = useTranslation();

  return (
    <Paper component={Link} to={`/dashboard/${summary.provider.toLowerCase()}`} withBorder p="md" radius="md" shadow="sm" style={{ textDecoration: 'none' }}>
      <Title order={4}>{summary.provider}</Title>
      <Text c="dimmed" size="sm" mb="sm">{t('dashboard.provider.totalAlerts', 'Total de Alertas')}: {summary.total_alerts}</Text>
      <Group >
        {Object.entries(summary.by_severity).map(([severity, count]) => (
          <Badge key={severity} color={severityColors[severity] || 'gray'} variant="light">
            {t(`severity.${severity}`, severity)}: {count}
          </Badge>
        ))}
      </Group>
    </Paper>
  );
};

export default ProviderSummaryCard;
