import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Title, Paper, Text, Group, Select, Button as MantineButton, SimpleGrid, Box, Alert as MantineAlert } from '@mantine/core';
import { BarChart, PieChart } from '@mantine/charts';
import { IconAlertCircle } from '@tabler/icons-react';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import AlertsTable, { Alert as AlertType } from '../components/Dashboard/AlertsTable';

// Tipos para os dados dos gráficos
interface ChartDataItem {
  name: string;
  value: number;
  color?: string;
}

/**
 * `ReportsPage` é um componente de página que exibe vários relatórios de segurança
 * com base nos dados de alertas. Inclui filtros por período e visualizações
 * como contagem de alertas por severidade, por provedor e uma lista de alertas abertos.
 *
 * @component
 */
const ReportsPage: React.FC = () => {
  const { t } = useTranslation();
  const auth = useAuth();
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [allAlerts, setAllAlerts] = useState<AlertType[]>([]);
  const [timeRange, setTimeRange] = useState<string>('last7days');

  const apiClient = useMemo(() => {
    return axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
      headers: { 'Authorization': `Bearer ${auth.token}` }
    });
  }, [auth.token]);

  /**
   * Busca todos os dados de alertas da API.
   * Atualmente, busca um grande número de alertas e aplica filtros no frontend.
   * Considerar otimizações futuras com filtros de data na API.
   */
  const fetchAlertsData = async () => {
    if (!auth.isAuthenticated) return;
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<AlertType[]>('/alerts?limit=1000&sort_by=created_at&sort_order=desc');
      setAllAlerts(response.data || []);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || t('reportsPage.errorFetchingAlerts', 'Erro ao buscar alertas.');
      setError(t('reportsPage.errorFetchingAlertsDetails', { error: errorMessage }));
      setAllAlerts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (auth.isAuthenticated) {
        fetchAlertsData();
    }
  }, [auth.isAuthenticated]);

  const filteredAlertsByTime = useMemo(() => {
    if (timeRange === 'allTime' || !allAlerts.length) {
      return allAlerts;
    }
    const now = new Date();
    const daysToSubtract = timeRange === 'last7days' ? 7 : 30;
    // Cria uma nova data para não modificar 'now' diretamente com setDate
    const startDate = new Date(new Date().setDate(now.getDate() - daysToSubtract));

    return allAlerts.filter(alert => {
      const alertDate = new Date(alert.created_at);
      return alertDate >= startDate;
    });
  }, [allAlerts, timeRange]);

  const severityData = useMemo<ChartDataItem[]>(() => {
    const counts: Record<string, number> = {};
    filteredAlertsByTime.forEach(alert => {
      counts[alert.severity] = (counts[alert.severity] || 0) + 1;
    });
    // Adicionar cores padrão para severidades conhecidas
    return Object.entries(counts).map(([name, value]) => {
        let color;
        switch(name.toLowerCase()) {
            case 'critical': color = 'var(--mantine-color-red-6)'; break;
            case 'high': color = 'var(--mantine-color-orange-6)'; break;
            case 'medium': color = 'var(--mantine-color-yellow-5)'; break;
            case 'low': color = 'var(--mantine-color-blue-5)'; break;
            case 'informational': color = 'var(--mantine-color-gray-5)'; break;
            default: color = 'var(--mantine-color-teal-5)'; // Cor genérica
        }
        return { name, value, color };
    });
  }, [filteredAlertsByTime]);

  const providerData = useMemo<ChartDataItem[]>(() => {
    const counts: Record<string, number> = {};
    filteredAlertsByTime.forEach(alert => {
      counts[alert.provider.toUpperCase()] = (counts[alert.provider.toUpperCase()] || 0) + 1;
    });
     // Adicionar cores padrão para provedores conhecidos
    return Object.entries(counts).map(([name, value]) => {
        let color;
        switch(name.toLowerCase()) {
            case 'aws': color = 'var(--mantine-color-orange-7)'; break;
            case 'gcp': color = 'var(--mantine-color-blue-7)'; break;
            case 'azure': color = 'var(--mantine-color-indigo-7)'; break;
            case 'huawei': color = 'var(--mantine-color-red-7)'; break;
            case 'googleworkspace': color = 'var(--mantine-color-green-7)'; break;
            default: color = 'var(--mantine-color-cyan-7)';
        }
        return { name, value, color };
    });
  }, [filteredAlertsByTime]);

  const openAlertsForTable = useMemo(() => {
    return filteredAlertsByTime.filter(alert => alert.status === 'OPEN');
  }, [filteredAlertsByTime]);

   const mockUpdateStatus = async (alertId: number, newStatus: string) => {
    // Não faz nada, pois a página de relatórios é para visualização
    // Apenas loga para o console se necessário para depuração
    // console.warn(`Attempted to update status for alert ${alertId} to ${newStatus} from reports page.`);
  };

  return (
    <div className="reports-page" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <Title order={1} ta="center" mb="xl">{t('reportsPage.title', 'Relatórios de Segurança')}</Title>

      <Paper withBorder p="md" mb="xl" shadow="xs" radius="md">
        <Group>
          <Select
            label={t('reportsPage.timeRangeFilterLabel', 'Período')}
            value={timeRange}
            onChange={(value) => setTimeRange(value || 'last7days')}
            data={[
              { value: 'last7days', label: t('reportsPage.last7Days', 'Últimos 7 dias') },
              { value: 'last30days', label: t('reportsPage.last30Days', 'Últimos 30 dias') },
              { value: 'allTime', label: t('reportsPage.allTime', 'Todo o período') },
            ]}
            style={{width: '200px'}}
            disabled={loading}
          />
          <MantineButton onClick={fetchAlertsData} loading={loading}>
            {t('reportsPage.refreshDataButton', 'Atualizar Dados')}
          </MantineButton>
        </Group>
      </Paper>

      {loading && <Text mt="md">{t('reportsPage.loadingData', 'Carregando dados dos relatórios...')}</Text>}
      {error && (
        <MantineAlert
            icon={<IconAlertCircle size="1rem" />}
            title={t('reportsPage.errorTitle', 'Erro ao Carregar Relatórios')}
            color="red"
            withCloseButton
            onClose={() => setError(null)}
            mt="md"
        >
            {error}
        </MantineAlert>
      )}

      {!loading && !error && (
        <>
          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="xl" mt="xl">
            <Paper withBorder p="md" shadow="sm" radius="md">
              <Title order={3} mb="md" ta="center">{t('reportsPage.alertsBySeverityTitle', 'Alertas por Severidade')}</Title>
              {severityData.length > 0 ? (
                <Box h={300}>
                  <PieChart
                    h={300}
                    data={severityData}
                    withTooltip
                    tooltipDataSource="segment" // Mostra dados do segmento no tooltip
                    valueFormatter={(value) => value.toLocaleString()} // Formata o valor no tooltip
                  />
                </Box>
              ) : (
                <Text ta="center">{t('reportsPage.noDataForSeverityChart', 'Sem dados para o gráfico de severidade.')}</Text>
              )}
            </Paper>

            <Paper withBorder p="md" shadow="sm" radius="md">
              <Title order={3} mb="md" ta="center">{t('reportsPage.alertsByProviderTitle', 'Alertas por Provedor')}</Title>
              {providerData.length > 0 ? (
                <Box h={300}>
                  <BarChart
                    h={300}
                    data={providerData}
                    dataKey="name"
                    series={[{ name: 'value', color: 'blue.6', label: t('reportsPage.countLabel', 'Contagem') }]} // A cor aqui é para a legenda, as cores das barras vêm do `data`
                    tickLine="y"
                    yAxisProps={{ domain: [0, 'auto'] }}
                    valueFormatter={(value) => value.toLocaleString()}
                    barProps={{
                        // A cor é definida por item no `providerData`
                    }}
                  />
                </Box>
              ) : (
                <Text ta="center">{t('reportsPage.noDataForProviderChart', 'Sem dados para o gráfico de provedor.')}</Text>
              )}
            </Paper>
          </SimpleGrid>

          <Paper withBorder p="md" shadow="sm" radius="md" mt="xl">
            <Title order={3} mb="md">
              {t('reportsPage.openAlertsTitle', 'Alertas Abertos')} ({timeRange === 'last7days' ? t('reportsPage.last7Days') : timeRange === 'last30days' ? t('reportsPage.last30Days') : t('reportsPage.allTime')})
            </Title>
            {openAlertsForTable.length > 0 ? (
                <AlertsTable
                    alerts={openAlertsForTable}
                    title=""
                    onUpdateStatus={mockUpdateStatus}
                    canUpdateStatus={false}
                />
            ) : (
                <Text>{t('reportsPage.noOpenAlerts', 'Nenhum alerta aberto encontrado para o período selecionado.')}</Text>
            )}
          </Paper>
        </>
      )}
    </div>
  );
};

export default ReportsPage;
