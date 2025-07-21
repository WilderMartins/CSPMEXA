import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Container, Title, Grid, Paper, Text, Space } from '@mantine/core';
import { api } from '../../services/api';
import ErrorMessage from '../../components/Common/ErrorMessage';
import SecurityDonutChart from '../../components/Dashboard/SecurityDonutChart';
import ProviderSummaryCard from '../../components/Dashboard/ProviderSummaryCard';

interface ProviderSummary {
  provider: string;
  total_alerts: number;
  by_severity: { [key: string]: number };
}

const ConsolidatedDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const [summaries, setSummaries] = useState<ProviderSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSummaries = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.get<ProviderSummary[]>('/dashboard/consolidated_summary');
        setSummaries(response.data);
      } catch (err: any) {
        const errorMessage = err.response?.data?.detail || err.message;
        setError(t('dashboard.errors.loadingFailed', { error: errorMessage }));
      } finally {
        setLoading(false);
      }
    };

    fetchSummaries();
  }, [t]);

  const chartData = summaries.map(s => ({
    name: s.provider,
    value: s.total_alerts,
  }));

  return (
    <Container fluid>
      <Title order={1} mb="lg">{t('dashboard.consolidated.title', 'Visão Geral Consolidada')}</Title>

      <ErrorMessage message={error} onClose={() => setError(null)} />

      {loading ? (
        <Text>{t('dashboard.loading', 'Carregando...')}</Text>
      ) : (
        <Grid>
          <Grid.Col span={{ base: 12, md: 4 }}>
            <Paper withBorder p="md" radius="md" style={{ height: '100%' }}>
              <Title order={3} ta="center" mb="md">{t('dashboard.consolidated.securityPosture', 'Postura de Segurança Geral')}</Title>
              <SecurityDonutChart data={chartData} />
            </Paper>
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 8 }}>
            <Grid>
              {summaries.map(summary => (
                <Grid.Col key={summary.provider} span={{ base: 12, sm: 6, lg: 4 }}>
                  <ProviderSummaryCard summary={summary} />
                </Grid.Col>
              ))}
            </Grid>
          </Grid.Col>
        </Grid>
      )}
       <Space h="xl" />
    </Container>
  );
};

export default ConsolidatedDashboardPage;
