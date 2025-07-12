import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Title, Box, Skeleton } from '@mantine/core';
import ProviderAnalysisSection from '../../components/Dashboard/ProviderAnalysisSection';
import AlertsTable, { Alert as AlertType } from '../../components/Dashboard/AlertsTable';
import ErrorMessage from '../../components/Common/ErrorMessage';

const M365DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const auth = useAuth();

  const [alerts, setAlerts] = useState<AlertType[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisType, setAnalysisType] = useState<string | null>(null);

  const apiClient = useMemo(() => {
    return axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
      headers: { 'Authorization': `Bearer ${auth.token}` }
    });
  }, [auth.token]);

  const handleAnalysis = async (provider: string, servicePath: string, currentAnalysisType: string) => {
    setIsLoading(true);
    setError(null);
    setAlerts([]);
    setAnalysisType(currentAnalysisType);

    const fullUrl = `/analyze/m365/${servicePath}`;

    try {
      const response = await apiClient.post<AlertType[]>(fullUrl, {});
      setAlerts(response.data || []);
      if (response.data.length === 0) {
        setError(t('dashboardPage.noNewAlertsForAnalysis', { type: currentAnalysisType }));
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message;
      setError(t('dashboardPage.errorDuringAnalysis', { type: currentAnalysisType, provider: 'Microsoft 365', error: errorMessage }));
    } finally {
      setIsLoading(false);
    }
  };

  const providerConfig = {
    providerNameKey: 'dashboardPage.m365AnalysisTitle',
    inputFields: [], // M365 não precisa de inputs de ID na UI, pois são configurados no backend
    analysisButtons: [
      { id: 'm365Mfa', labelKey: 'dashboardPage.analyzeM365MfaButton', servicePath: 'users-mfa-status', analysisType: 'M365 Users MFA Status' },
      { id: 'm365Ca', labelKey: 'dashboardPage.analyzeM365CaButton', servicePath: 'conditional-access-policies', analysisType: 'M365 Conditional Access Policies' },
    ]
  };

  return (
    <div>
      <Title order={2} mb="xl">{t(providerConfig.providerNameKey, 'Microsoft 365 Analysis')}</Title>

      <ProviderAnalysisSection
        providerId="m365"
        inputFields={providerConfig.inputFields}
        analysisButtons={providerConfig.analysisButtons}
        onAnalyze={(provider, servicePath, currentAnalysisType) => handleAnalysis(provider, servicePath, currentAnalysisType)}
        isLoading={isLoading}
        currentAnalysisType={analysisType}
      />

      <ErrorMessage message={error} onClose={() => setError(null)} />

      {isLoading && !error && (
         <Box mt="xl">
            <Skeleton height={25} mt="md" />
            <Skeleton height={25} mt="xs" />
            <Skeleton height={25} mt="xs" />
          </Box>
      )}

      {!isLoading && !error && alerts.length > 0 && (
        <AlertsTable
          alerts={alerts}
          title={t('dashboardPage.alertsFoundFor', { type: analysisType })}
          onUpdateStatus={async () => {}}
          canUpdateStatus={false}
        />
      )}
    </div>
  );
};

export default M365DashboardPage;
