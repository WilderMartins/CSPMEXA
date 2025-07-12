import React from 'react';
import { useTranslation } from 'react-i18next';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Title, Text, Container } from '@mantine/core';

// Importar as novas páginas de análise por provedor
import AwsDashboardPage from './Dashboard/AwsDashboardPage';
import GcpDashboardPage from './Dashboard/GcpDashboardPage';
import AzureDashboardPage from './Dashboard/AzureDashboardPage';
import HuaweiDashboardPage from './Dashboard/HuaweiDashboardPage';
import GwsDashboardPage from './Dashboard/GwsDashboardPage';
import M365DashboardPage from './Dashboard/M365DashboardPage';

const DashboardHomePage = () => {
  const { t } = useTranslation();
  return (
    <Container>
      <Title order={2} ta="center" mt="xl">{t('dashboard.welcome.title', 'Welcome to the Dashboard')}</Title>
      <Text ta="center" mt="md" c="dimmed">{t('dashboard.welcome.subtitle', 'Select a provider from the menu to start an analysis.')}</Text>
    </Container>
  );
};

/**
 * `DashboardPage` agora atua como um roteador para as sub-páginas de cada provedor.
 * Ele renderiza a página de análise específica com base na URL.
 *
 * @component
 */
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