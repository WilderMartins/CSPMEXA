import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Title, Box, Skeleton } from '@mantine/core';
import ProviderAnalysisSection from '../../components/Dashboard/ProviderAnalysisSection';
import AlertsTable, { Alert as AlertType } from '../../components/Dashboard/AlertsTable';
import ErrorMessage from '../../components/Common/ErrorMessage';

const HuaweiDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const auth = useAuth();

  const [alerts, setAlerts] = useState<AlertType[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisType, setAnalysisType] = useState<string | null>(null);

  const [projectId, setProjectId] = useState<string>('');
  const [regionId, setRegionId] = useState<string>('');
  const [domainId, setDomainId] = useState<string>('');

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

    const region = idParams?.region_id?.trim();
    if (!region) {
        setError(t('dashboardPage.huaweiRegionIdRequired'));
        setIsLoading(false);
        return;
    }

    const queryParams = new URLSearchParams({ region_id: region });
    if (idParams?.project_id) queryParams.append('project_id', idParams.project_id.trim());
    if (idParams?.domain_id) queryParams.append('domain_id', idParams.domain_id.trim());

    const fullUrl = `/analyze/huawei/${servicePath}?${queryParams.toString()}`;

    try {
      const response = await apiClient.post<AlertType[]>(fullUrl, {});
      setAlerts(response.data || []);
      if (response.data.length === 0) {
        setError(t('dashboardPage.noNewAlertsForAnalysis', { type: currentAnalysisType }));
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message;
      setError(t('dashboardPage.errorDuringAnalysis', { type: currentAnalysisType, provider: 'Huawei', error: errorMessage }));
    } finally {
      setIsLoading(false);
    }
  };

  const providerConfig = {
    providerNameKey: 'dashboardPage.huaweiAnalysisTitle',
    inputFields: [
      { id: 'huaweiProjectIdInput', name: 'projectId', labelKey: 'dashboardPage.huaweiProjectIdLabel', placeholderKey: 'dashboardPage.huaweiProjectIdPlaceholder', value: projectId, setter: setProjectId, isOptional: true },
      { id: 'huaweiRegionIdInput', name: 'regionId', labelKey: 'dashboardPage.huaweiRegionIdLabel', placeholderKey: 'dashboardPage.huaweiRegionIdPlaceholder', value: regionId, setter: setRegionId },
      { id: 'huaweiDomainIdInput', name: 'domainId', labelKey: 'dashboardPage.huaweiDomainIdLabel', placeholderKey: 'dashboardPage.huaweiDomainIdPlaceholder', value: domainId, setter: setDomainId, isOptional: true }
    ],
    analysisButtons: [
      { id: 'huaweiObs', labelKey: 'dashboardPage.analyzeHuaweiOBSButton', servicePath: 'obs/buckets', analysisType: 'Huawei OBS Buckets', idParams: { project_id: projectId, region_id: regionId } },
      { id: 'huaweiEcs', labelKey: 'dashboardPage.analyzeHuaweiECSButton', servicePath: 'ecs/instances', analysisType: 'Huawei ECS Instances', idParams: { project_id: projectId, region_id: regionId } },
      { id: 'huaweiSgs', labelKey: 'dashboardPage.analyzeHuaweiSGsButton', servicePath: 'vpc/security-groups', analysisType: 'Huawei VPC SGs', idParams: { project_id: projectId, region_id: regionId } },
      { id: 'huaweiIamUsers', labelKey: 'dashboardPage.analyzeHuaweiIAMUsersButton', servicePath: 'iam/users', analysisType: 'Huawei IAM Users', idParams: { domain_id: domainId, region_id: regionId } },
    ]
  };

  return (
    <div>
      <Title order={2} mb="xl">{t(providerConfig.providerNameKey, 'Huawei Cloud Analysis')}</Title>

      <ProviderAnalysisSection
        providerId="huawei"
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

export default HuaweiDashboardPage;
