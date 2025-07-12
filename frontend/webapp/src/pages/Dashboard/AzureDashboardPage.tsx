import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Title, Box, Skeleton } from '@mantine/core';
import ProviderAnalysisSection from '../../components/Dashboard/ProviderAnalysisSection';
import AlertsTable, { Alert as AlertType } from '../../components/Dashboard/AlertsTable';
import ErrorMessage from '../../components/Common/ErrorMessage';

const AzureDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const auth = useAuth();

  const [alerts, setAlerts] = useState<AlertType[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisType, setAnalysisType] = useState<string | null>(null);

  const [subscriptionId, setSubscriptionId] = useState<string>('');

  const apiClient = useMemo(() => {
    return axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
      headers: { 'Authorization': `Bearer ${auth.token}` }
    });
  }, [auth.token]);

  const handleAnalysis = async (provider: string, servicePath: string, currentAnalysisType: string, idParams?: Record<string, string | undefined>) => {
    setIsLoading(true);
    setError(null);
    setAlerts([]);
    setAnalysisType(currentAnalysisType);

    const subId = idParams?.subscription_id?.trim();
    const guidRegex = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;
    if (!subId) {
      setError(t('dashboardPage.azureSubscriptionIdRequired'));
      setIsLoading(false);
      return;
    }
    if (!guidRegex.test(subId)) {
        setError(t('dashboardPage.azureSubscriptionIdInvalid'));
        setIsLoading(false);
        return;
    }

    const queryParams = new URLSearchParams({ subscription_id: subId });
    const fullUrl = `/analyze/azure/${servicePath}?${queryParams.toString()}`;

    try {
      const response = await apiClient.post<AlertType[]>(fullUrl, {});
      setAlerts(response.data || []);
      if (response.data.length === 0) {
        setError(t('dashboardPage.noNewAlertsForAnalysis', { type: currentAnalysisType }));
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message;
      setError(t('dashboardPage.errorDuringAnalysis', { type: currentAnalysisType, provider: 'Azure', error: errorMessage }));
    } finally {
      setIsLoading(false);
    }
  };

  const providerConfig = {
    providerNameKey: 'dashboardPage.azureAnalysisTitle',
    inputFields: [
      { id: 'azureSubId', name: 'subscriptionId', labelKey: 'dashboardPage.azureSubscriptionIdLabel', placeholderKey: 'dashboardPage.azureSubscriptionIdPlaceholder', value: subscriptionId, setter: setSubscriptionId }
    ],
    analysisButtons: [
      { id: 'azureVms', labelKey: 'dashboardPage.analyzeAzureVMsButton', servicePath: 'virtualmachines', analysisType: 'Azure Virtual Machines', idParams: { subscription_id: subscriptionId } },
      { id: 'azureStorage', labelKey: 'dashboardPage.analyzeAzureStorageButton', servicePath: 'storageaccounts', analysisType: 'Azure Storage Accounts', idParams: { subscription_id: subscriptionId } },
    ]
  };

  return (
    <div>
      <Title order={2} mb="xl">{t(providerConfig.providerNameKey, 'Azure Analysis')}</Title>

      <ProviderAnalysisSection
        providerId="azure"
        inputFields={providerConfig.inputFields}
        analysisButtons={providerConfig.analysisButtons}
        onAnalyze={(provider, servicePath, currentAnalysisType, idParams) => handleAnalysis(provider, servicePath, currentAnalysisType, idParams)}
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

export default AzureDashboardPage;
