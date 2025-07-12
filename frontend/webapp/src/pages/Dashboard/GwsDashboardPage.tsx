import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Title, Box, Skeleton } from '@mantine/core';
import ProviderAnalysisSection from '../../components/Dashboard/ProviderAnalysisSection';
import AlertsTable, { Alert as AlertType } from '../../components/Dashboard/AlertsTable';
import ErrorMessage from '../../components/Common/ErrorMessage';

const GwsDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const auth = useAuth();

  const [alerts, setAlerts] = useState<AlertType[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisType, setAnalysisType] = useState<string | null>(null);

  const [customerId, setCustomerId] = useState<string>('my_customer');
  const [adminEmail, setAdminEmail] = useState<string>('');

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

    const email = idParams?.admin_email?.trim();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (email && !emailRegex.test(email)) {
        setError(t('dashboardPage.gwsAdminEmailInvalid'));
        setIsLoading(false);
        return;
    }

    const queryParams = new URLSearchParams();
    if (idParams?.customer_id) queryParams.append('customer_id', idParams.customer_id.trim());
    if (email) queryParams.append('delegated_admin_email', email);

    const fullUrl = `/analyze/googleworkspace/${servicePath}?${queryParams.toString()}`;

    try {
      const response = await apiClient.post<AlertType[]>(fullUrl, {});
      setAlerts(response.data || []);
      if (response.data.length === 0) {
        setError(t('dashboardPage.noNewAlertsForAnalysis', { type: currentAnalysisType }));
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message;
      setError(t('dashboardPage.errorDuringAnalysis', { type: currentAnalysisType, provider: 'Google Workspace', error: errorMessage }));
    } finally {
      setIsLoading(false);
    }
  };

  const providerConfig = {
    providerNameKey: 'dashboardPage.gwsAnalysisTitle',
    inputFields: [
      { id: 'gwsCustomerId', name: 'customerId', labelKey: 'dashboardPage.gwsCustomerIdLabel', placeholderKey: 'dashboardPage.gwsCustomerIdPlaceholder', value: customerId, setter: setCustomerId, isOptional: true },
      { id: 'gwsAdminEmail', name: 'adminEmail', labelKey: 'dashboardPage.gwsAdminEmailLabel', placeholderKey: 'dashboardPage.gwsAdminEmailPlaceholder', value: adminEmail, setter: setAdminEmail, isOptional: true },
    ],
    analysisButtons: [
      { id: 'gwsUsers', labelKey: 'dashboardPage.analyzeGWSUsersButton', servicePath: 'users', analysisType: 'Google Workspace Users', idParams: { customer_id: customerId, admin_email: adminEmail } },
      { id: 'gwsSharedDrives', labelKey: 'dashboardPage.analyzeGWSSharedDrivesButton', servicePath: 'drive/shared-drives', analysisType: 'Google Workspace Shared Drives', idParams: { customer_id: customerId, admin_email: adminEmail } },
    ]
  };

  return (
    <div>
      <Title order={2} mb="xl">{t(providerConfig.providerNameKey, 'Google Workspace Analysis')}</Title>

      <ProviderAnalysisSection
        providerId="googleworkspace"
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

export default GwsDashboardPage;
