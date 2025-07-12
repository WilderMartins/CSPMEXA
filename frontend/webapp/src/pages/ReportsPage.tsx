import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Title, Paper, Text, Group, Select, Button as MantineButton, SimpleGrid, Box, Skeleton } from '@mantine/core';
import { BarChart, PieChart } from '@mantine/charts';
// IconAlertCircle não é mais necessário diretamente aqui se ErrorMessage o encapsula
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import AlertsTable, { Alert as AlertType } from '../components/Dashboard/AlertsTable';
import ErrorMessage from '../components/Common/ErrorMessage';
import { calculateSeverityData, calculateProviderData, ChartDataItem } from '../utils/reportUtils'; // Importar funções utilitárias

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
      // TODO: Otimizar esta chamada de API.
      // Atualmente, busca todos os alertas (até o limite) e filtra no frontend.
      // Idealmente, a API deveria aceitar parâmetros como:
      // - date_from, date_to (para filtrar por período diretamente no backend)
      // - status (para buscar apenas 'OPEN' para certos relatórios)
      // - campos_para_agregar (para que o backend já retorne dados agregados para gráficos)
      // Exemplo de chamada otimizada: apiClient.get<AggregatedData>('/alerts/summary?period=last7days&group_by=severity')
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

  // TODO: Esta filtragem por tempo deve ser movida para o backend quando a API for otimizada.
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

  // TODO: Esta agregação deve ser movida para o backend quando a API for otimizada.
  const severityData = useMemo<ChartDataItem[]>(() => calculateSeverityData(filteredAlertsByTime), [filteredAlertsByTime]);

  // TODO: Esta agregação deve ser movida para o backend quando a API for otimizada.
  const providerData = useMemo<ChartDataItem[]>(() => calculateProviderData(filteredAlertsByTime), [filteredAlertsByTime]);

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

      <ErrorMessage message={error} onClose={() => setError(null)} title={t('reportsPage.errorTitle', 'Report Error')} />

      {loading && !error && (
        <>
          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="xl" mt="xl">
            <Paper withBorder p="md" shadow="sm" radius="md">
              <Skeleton height={30} width="60%" mx="auto" mb="md" /> {/* Title Skeleton */}
              <Skeleton height={300} /> {/* Chart Skeleton */}
            </Paper>
            <Paper withBorder p="md" shadow="sm" radius="md">
              <Skeleton height={30} width="60%" mx="auto" mb="md" /> {/* Title Skeleton */}
              <Skeleton height={300} /> {/* Chart Skeleton */}
            </Paper>
          </SimpleGrid>
          <Paper withBorder p="md" shadow="sm" radius="md" mt="xl">
            <Skeleton height={30} width="40%" mb="md" /> {/* Title Skeleton */}
            <Skeleton height={25} mt="md" /> {/* Table Row Skeleton */}
            <Skeleton height={25} mt="xs" />
            <Skeleton height={25} mt="xs" />
          </Paper>
        </>
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
