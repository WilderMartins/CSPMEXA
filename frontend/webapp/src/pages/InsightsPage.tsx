import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Title, Paper, Text, Group, Button as MantineButton, SimpleGrid, Box, List, ThemeIcon, Skeleton } from '@mantine/core';
// import { BarChart } from '@mantine/charts'; // BarChart pode ser usado no futuro
import { IconListCheck, IconTargetArrow, IconRefresh } from '@tabler/icons-react';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { Alert as AlertType } from '../components/Dashboard/AlertsTable';
import ErrorMessage from '../components/Common/ErrorMessage';
import { calculateTopViolatedPolicies, calculateTopVulnerableResources, InsightDataItem } from '../utils/insightUtils';

/**
 * `InsightsPage` é um componente de página que exibe insights de segurança
 * derivados dos dados de alertas. Atualmente, foca em apresentar as "Top 5 Políticas Mais Violadas"
 * e os "Top 5 Recursos Mais Vulneráveis" com base nos alertas abertos.
 *
 * @component
 */
const InsightsPage: React.FC = () => {
  const { t } = useTranslation();
  const auth = useAuth();
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [allAlerts, setAllAlerts] = useState<AlertType[]>([]);

  const apiClient = useMemo(() => {
    return axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
      headers: { 'Authorization': `Bearer ${auth.token}` }
    });
  }, [auth.token]);

  /**
   * Busca dados de alertas abertos da API para gerar insights.
   */
  const fetchAlertsData = async () => {
    if (!auth.isAuthenticated) return;
    setLoading(true);
    setError(null);
    try {
      // TODO: Otimizar esta chamada de API.
      // Atualmente, busca todos os alertas ABERTOS (até o limite) e processa no frontend.
      // Idealmente, a API poderia fornecer endpoints de agregação para gerar esses insights diretamente no backend.
      // Ex: /alerts/insights?type=top_policies ou /alerts/insights?type=top_resources
      const response = await apiClient.get<AlertType[]>('/alerts?limit=1000&status=OPEN&sort_by=created_at&sort_order=desc');
      setAllAlerts(response.data || []);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || t('insightsPage.errorFetchingAlerts', 'Erro ao buscar alertas.');
      setError(t('insightsPage.errorFetchingAlertsDetails', { error: errorMessage }));
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

  // TODO: Esta agregação para 'Top Políticas Violadas' deve ser movida para o backend quando a API for otimizada.
  const topViolatedPolicies = useMemo<InsightDataItem[]>(() => calculateTopViolatedPolicies(allAlerts, 5), [allAlerts]);

  // TODO: Esta agregação para 'Top Recursos Vulneráveis' deve ser movida para o backend quando a API for otimizada.
  const topVulnerableResources = useMemo<InsightDataItem[]>(() => calculateTopVulnerableResources(allAlerts, 5), [allAlerts]);

  return (
    <div className="insights-page" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <Title order={1} ta="center" mb="xl">{t('insightsPage.title', 'Insights de Segurança')}</Title>

      <Paper withBorder p="md" mb="xl" shadow="xs" radius="md">
        <Group>
          <MantineButton onClick={fetchAlertsData} loading={loading} leftSection={<IconRefresh size={18}/>}>
            {t('insightsPage.refreshDataButton', 'Atualizar Insights (Alertas Abertos)')}
          </MantineButton>
        </Group>
        <Text size="sm" c="dimmed" mt="xs">
            {t('insightsPage.description', 'Esta página analisa os alertas ABERTOS para fornecer informações sobre as principais vulnerabilidades e políticas violadas.')}
        </Text>
      </Paper>

      <ErrorMessage message={error} onClose={() => setError(null)} title={t('insightsPage.errorTitle', 'Insight Error')} />

      {loading && !error && (
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="xl" mt="xl">
            <Paper withBorder p="xl" shadow="sm" radius="md">
                <Skeleton height={30} width="70%" mx="auto" mb="lg" />
                <Skeleton height={20} mt="md" />
                <Skeleton height={20} mt="xs" />
                <Skeleton height={20} mt="xs" />
                <Skeleton height={20} mt="xs" />
                <Skeleton height={20} mt="xs" />
            </Paper>
            <Paper withBorder p="xl" shadow="sm" radius="md">
                <Skeleton height={30} width="70%" mx="auto" mb="lg" />
                <Skeleton height={20} mt="md" />
                <Skeleton height={20} mt="xs" />
                <Skeleton height={20} mt="xs" />
                <Skeleton height={20} mt="xs" />
                <Skeleton height={20} mt="xs" />
            </Paper>
        </SimpleGrid>
      )}

      {!loading && !error && allAlerts.length === 0 && (
        <Text mt="xl" ta="center" size="lg" c="dimmed">
            {t('insightsPage.noOpenAlerts', 'Nenhum alerta aberto encontrado para gerar insights no momento.')}
        </Text>
      )}

      {!loading && !error && allAlerts.length > 0 && (
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="xl" mt="xl">
          <Paper withBorder p="xl" shadow="sm" radius="md">
            <Title order={3} mb="lg" ta="center">
              <Group justify='center' gap="xs">
                <ThemeIcon variant="light" size="lg" color="blue"><IconListCheck size={22} /></ThemeIcon>
                {t('insightsPage.topViolatedPoliciesTitle', 'Top 5 Políticas Mais Violadas')}
              </Group>
            </Title>
            {topViolatedPolicies.length > 0 ? (
              <List spacing="md" size="sm" center>
                {topViolatedPolicies.map((policy, index) => (
                  <List.Item
                    key={index}
                    icon={
                      <ThemeIcon color="blue" size={28} radius="xl">
                        <Text fw={700} fz="sm">{index + 1}</Text>
                      </ThemeIcon>
                    }
                  >
                    <Text span fw={500} fz="md">{policy.name}</Text>
                    <Text span c="dimmed" fz="sm"> ({policy.count} {policy.count === 1 ? t('insightsPage.alertSuffixSingular', 'alerta') : t('insightsPage.alertsSuffixPlural', 'alertas')})</Text>
                  </List.Item>
                ))}
              </List>
            ) : (
              <Text ta="center" c="dimmed">{t('insightsPage.noPolicyData', 'Não há dados de políticas violadas para exibir.')}</Text>
            )}
          </Paper>

          <Paper withBorder p="xl" shadow="sm" radius="md">
            <Title order={3} mb="lg" ta="center">
                <Group justify='center' gap="xs">
                    <ThemeIcon variant="light" size="lg" color="orange"><IconTargetArrow size={22} /></ThemeIcon>
                    {t('insightsPage.topVulnerableResourcesTitle', 'Top 5 Recursos Mais Vulneráveis')}
                </Group>
            </Title>
            {topVulnerableResources.length > 0 ? (
               <List spacing="md" size="sm" center>
                {topVulnerableResources.map((resource, index) => (
                  <List.Item
                    key={index}
                    icon={
                        <ThemeIcon color="orange" size={28} radius="xl">
                            <Text fw={700} fz="sm">{index + 1}</Text>
                        </ThemeIcon>
                    }
                  >
                     <Text span fw={500} fz="md">{resource.name}</Text>
                     <Text span c="dimmed" fz="sm"> ({resource.count} {resource.count === 1 ? t('insightsPage.alertSuffixSingular', 'alerta') : t('insightsPage.alertsSuffixPlural', 'alertas')})</Text>
                  </List.Item>
                ))}
              </List>
            ) : (
              <Text ta="center" c="dimmed">{t('insightsPage.noResourceData', 'Não há dados de recursos vulneráveis para exibir.')}</Text>
            )}
          </Paper>
        </SimpleGrid>
      )}
    </div>
  );
};

export default InsightsPage;
