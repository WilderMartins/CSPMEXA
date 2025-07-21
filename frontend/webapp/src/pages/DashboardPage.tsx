import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Title, Text, Container, Grid, Space } from '@mantine/core';
import { api } from '../services/api';

// Importar componentes do Dashboard
import SummaryCards from '../components/Dashboard/SummaryCards';
import AlertsBySeverityChart from '../components/Dashboard/AlertsBySeverityChart';

// Importar as páginas de análise por provedor
import AwsDashboardPage from './Dashboard/AwsDashboardPage';
import GcpDashboardPage from './Dashboard/GcpDashboardPage';
import AzureDashboardPage from './Dashboard/AzureDashboardPage';
import HuaweiDashboardPage from './Dashboard/HuaweiDashboardPage';
import GwsDashboardPage from './Dashboard/GwsDashboardPage';
import M365DashboardPage from './Dashboard/M365DashboardPage';

interface SummaryData {
  total_alerts: number;
  by_severity: { [key: string]: number };
  by_status: { [key: string]: number };
}

const DashboardHomePage = () => {
  const { t } = useTranslation();
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get<SummaryData>('/dashboard/summary')
      .then(response => {
        setSummary(response.data);
        setLoading(false);
      })
      .catch(error => {
        console.error('Error fetching summary data:', error);
        setLoading(false);
      });
  }, []);

  return (
    <Container fluid>
      <Title order={1} mb="lg">{t('dashboard.title', 'Visão Geral de Segurança')}</Title>

      {loading ? (
        <Text>Carregando dashboard...</Text>
      ) : summary ? (
        <>
          <SummaryCards />
          <Space h="xl" />
          <Grid>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <AlertsBySeverityChart data={summary.by_severity} />
            </Grid.Col>
            {/* Outros gráficos ou tabelas podem ser adicionados aqui */}
          </Grid>
        </>
      ) : (
        <Text c="red">Não foi possível carregar os dados do dashboard.</Text>
      )}
    </Container>
  );
};

const DashboardPage: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<DashboardHomePage />} />
      <Route path="aws" element={<AwsDashboardPage />} />
      <Route path="gcp" element={<GcpDashboardPage />} />
      <Route path="azure" element={<AzureDashboardPage />} />
      <Route path="huawei" element={<HuaweiDashboardPage />} />
      <Route path="google-workspace" element={<GwsDashboardPage />} />
      <Route path="microsoft365" element={<M365DashboardPage />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};

export default DashboardPage;