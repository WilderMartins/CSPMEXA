import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import ProviderAnalysisSection from '../components/Dashboard/ProviderAnalysisSection';
import AlertsTable, { Alert } from '../components/Dashboard/AlertsTable';
import { Tabs, Button as MantineButton, Title, Paper, Text } from '@mantine/core'; // Importar Tabs e outros componentes Mantine

// As definições de Paper e Title locais devem ser removidas se não foram antes.
// Por segurança, vamos garantir que não estão aqui.

const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const auth = useAuth();

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [gcpProjectId, setGcpProjectId] = useState<string>('');
  const [huaweiProjectId, setHuaweiProjectId] = useState<string>('');
  const [huaweiRegionId, setHuaweiRegionId] = useState<string>('');
  const [huaweiDomainId, setHuaweiDomainId] = useState<string>('');
  const [azureSubscriptionId, setAzureSubscriptionId] = useState<string>('');
  const [googleWorkspaceCustomerId, setGoogleWorkspaceCustomerId] = useState<string>('my_customer');
  const [googleWorkspaceAdminEmail, setGoogleWorkspaceAdminEmail] = useState<string>('');

  const [currentDisplayMode, setCurrentDisplayMode] = useState<'all_alerts' | 'analysis_result'>('all_alerts');
  const [currentAnalysisType, setCurrentAnalysisType] = useState<string | null>(null);

  const apiClient = useMemo(() => {
    return axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
      headers: { 'Authorization': `Bearer ${auth.token}` }
    });
  }, [auth.token]);

  const fetchAllAlerts = async () => {
    if (!auth.isAuthenticated) return;
    setIsLoading(true);
    setError(null);
    setAlerts([]);
    setCurrentDisplayMode('all_alerts');
    setCurrentAnalysisType(null);
    try {
      const response = await apiClient.get<Alert[]>('/alerts?limit=100&sort_by=last_seen_at&sort_order=desc'); // Tipar a resposta
      setAlerts(response.data || []);
      if (response.data.length === 0) setError(t('dashboardPage.noAlertsFound'));
    } catch (err: any) {
      console.error("Erro ao buscar todos os alertas:", err);
      const errorMessage = err.response?.data?.detail || err.message || t('dashboardPage.errorFetchingAlerts');
      setError(t('dashboardPage.errorFetchingAllAlerts', { error: errorMessage }));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (auth.isAuthenticated) {
      fetchAllAlerts();
    }
  }, [auth.isAuthenticated, apiClient]);

  const handleAnalysis = async (
    provider: 'aws' | 'gcp' | 'huawei' | 'azure' | 'googleworkspace',
    servicePath: string,
    analysisType: string,
    idParams?: Record<string, string | undefined>
  ) => {
    setIsLoading(true);
    setError(null);
    setAlerts([]);
    setCurrentDisplayMode('analysis_result');
    setCurrentAnalysisType(analysisType);

    let url = `/analyze/${provider}/${servicePath}`;
    const queryParams = new URLSearchParams();

    if (provider === 'gcp' && idParams?.projectId) queryParams.append('project_id', idParams.projectId);
    else if (provider === 'gcp' && !idParams?.projectId) { setError(t('dashboardPage.gcpProjectIdRequired')); setIsLoading(false); return; }

    if (provider === 'huawei') {
      if (idParams?.regionId) queryParams.append('region_id', idParams.regionId);
      else { setError(t('dashboardPage.huaweiRegionIdRequired')); setIsLoading(false); return; }
      if (idParams.projectId) queryParams.append('project_id', idParams.projectId);
      else if (servicePath !== 'iam/users') { setError(t('dashboardPage.huaweiProjectIdRequired')); setIsLoading(false); return;}
      if (servicePath === 'iam/users' && idParams.domainId) queryParams.append('domain_id', idParams.domainId);
    }

    if (provider === 'azure' && idParams?.subscriptionId) queryParams.append('subscription_id', idParams.subscriptionId);
    else if (provider === 'azure' && !idParams?.subscriptionId) { setError(t('dashboardPage.azureSubscriptionIdRequired')); setIsLoading(false); return; }

    if (provider === 'googleworkspace') {
      if (idParams?.gwsCustomerId) queryParams.append('customer_id', idParams.gwsCustomerId);
      if (idParams?.gwsAdminEmail) queryParams.append('delegated_admin_email', idParams.gwsAdminEmail);
    }

    const queryString = queryParams.toString();
    if (queryString) url += `?${queryString}`;

    try {
      const response = await apiClient.post<Alert[]>(url, {}); // Tipar a resposta
      setAlerts(response.data || []);
      if (response.data.length === 0) setError(t('dashboardPage.noNewAlertsForAnalysis', { type: analysisType }));
    } catch (err: any) {
      console.error(`Erro ao analisar ${analysisType} (${provider}):`, err);
      const errorMessage = err.response?.data?.detail || err.message || t('dashboardPage.errorFetchingAlerts');
      setError(t('dashboardPage.errorDuringAnalysis', { type: analysisType, provider: provider.toUpperCase(), error: errorMessage }));
    } finally {
      setIsLoading(false);
    }
  };

  const providerConfigs = {
    aws: {
      providerNameKey: 'dashboardPage.awsAnalysisTitle',
      analysisButtons: [
        { id: 's3', labelKey: 'dashboardPage.analyzeS3Button', servicePath: 's3', analysisType: 'AWS S3 Buckets' },
        { id: 'ec2Instances', labelKey: 'dashboardPage.analyzeEC2InstancesButton', servicePath: 'ec2/instances', analysisType: 'AWS EC2 Instances' },
        { id: 'ec2Sgs', labelKey: 'dashboardPage.analyzeEC2SGsButton', servicePath: 'ec2/security-groups', analysisType: 'AWS EC2 Security Groups' },
        { id: 'iamUsers', labelKey: 'dashboardPage.analyzeIAMUsersButton', servicePath: 'iam/users', analysisType: 'AWS IAM Users' },
        { id: 'rdsInstances', labelKey: 'dashboardPage.analyzeRDSInstancesButton', servicePath: 'rds/instances', analysisType: 'AWS RDS Instances' },
      ]
    },
    gcp: {
      providerNameKey: 'dashboardPage.gcpAnalysisTitle',
      inputFields: [
        { id: 'projectId', labelKey: 'dashboardPage.gcpProjectIdLabel', placeholderKey: 'dashboardPage.gcpProjectIdPlaceholder', value: gcpProjectId, setter: setGcpProjectId }
      ],
      analysisButtons: [
        { id: 'storage', labelKey: 'dashboardPage.analyzeGCPStorageButton', servicePath: 'storage/buckets', analysisType: 'GCP Storage Buckets', requiredParams: ['projectId'] },
        { id: 'computeInstances', labelKey: 'dashboardPage.analyzeGCPInstancesButton', servicePath: 'compute/instances', analysisType: 'GCP Compute Instances', requiredParams: ['projectId'] },
        { id: 'firewalls', labelKey: 'dashboardPage.analyzeGCPFirewallsButton', servicePath: 'compute/firewalls', analysisType: 'GCP Compute Firewalls', requiredParams: ['projectId'] },
        { id: 'iam', labelKey: 'dashboardPage.analyzeGCPIAMButton', servicePath: 'iam/project-policies', analysisType: 'GCP Project IAM', requiredParams: ['projectId'] },
        { id: 'gke', labelKey: 'dashboardPage.analyzeGKEClustersButton', servicePath: 'gke/clusters', analysisType: 'GCP GKE Clusters', requiredParams: ['projectId'] },
      ]
    },
    huawei: {
      providerNameKey: 'dashboardPage.huaweiAnalysisTitle',
      inputFields: [
        { id: 'projectId', labelKey: 'dashboardPage.huaweiProjectIdLabel', placeholderKey: 'dashboardPage.huaweiProjectIdPlaceholder', value: huaweiProjectId, setter: setHuaweiProjectId },
        { id: 'regionId', labelKey: 'dashboardPage.huaweiRegionIdLabel', placeholderKey: 'dashboardPage.huaweiRegionIdPlaceholder', value: huaweiRegionId, setter: setHuaweiRegionId },
        { id: 'domainId', labelKey: 'dashboardPage.huaweiDomainIdLabel', placeholderKey: 'dashboardPage.huaweiDomainIdPlaceholder', value: huaweiDomainId, setter: setHuaweiDomainId }
      ],
      analysisButtons: [
        { id: 'obs', labelKey: 'dashboardPage.analyzeHuaweiOBSButton', servicePath: 'obs/buckets', analysisType: 'Huawei OBS Buckets', requiredParams: ['projectId', 'regionId'] },
        { id: 'ecs', labelKey: 'dashboardPage.analyzeHuaweiECSButton', servicePath: 'ecs/instances', analysisType: 'Huawei ECS Instances', requiredParams: ['projectId', 'regionId'] },
        { id: 'sgs', labelKey: 'dashboardPage.analyzeHuaweiSGsButton', servicePath: 'vpc/security-groups', analysisType: 'Huawei VPC SGs', requiredParams: ['projectId', 'regionId'] },
        { id: 'iamUsers', labelKey: 'dashboardPage.analyzeHuaweiIAMButton', servicePath: 'iam/users', analysisType: 'Huawei IAM Users', requiredParams: ['regionId', 'domainId'] },
      ]
    },
    azure: {
      providerNameKey: 'dashboardPage.azureAnalysisTitle',
      inputFields: [
        { id: 'subscriptionId', labelKey: 'dashboardPage.azureSubscriptionIdLabel', placeholderKey: 'dashboardPage.azureSubscriptionIdPlaceholder', value: azureSubscriptionId, setter: setAzureSubscriptionId }
      ],
      analysisButtons: [
        { id: 'vms', labelKey: 'dashboardPage.analyzeAzureVMsButton', servicePath: 'virtualmachines', analysisType: 'Azure Virtual Machines', requiredParams: ['subscriptionId'] },
        { id: 'storage', labelKey: 'dashboardPage.analyzeAzureStorageButton', servicePath: 'storageaccounts', analysisType: 'Azure Storage Accounts', requiredParams: ['subscriptionId'] },
      ]
    },
    googleworkspace: {
      providerNameKey: 'dashboardPage.gwsAnalysisTitle',
      inputFields: [
        { id: 'gwsCustomerId', labelKey: 'dashboardPage.gwsCustomerIdLabel', placeholderKey: 'dashboardPage.gwsCustomerIdPlaceholder', value: googleWorkspaceCustomerId, setter: setGoogleWorkspaceCustomerId },
        { id: 'gwsAdminEmail', labelKey: 'dashboardPage.gwsAdminEmailLabel', placeholderKey: 'dashboardPage.gwsAdminEmailPlaceholder', value: googleWorkspaceAdminEmail, setter: setGoogleWorkspaceAdminEmail, type: 'email' }
      ],
      analysisButtons: [
        { id: 'gwsUsers', labelKey: 'dashboardPage.analyzeGWSUsersButton', servicePath: 'users', analysisType: 'Google Workspace Users', requiredParams: ['gwsCustomerId', 'gwsAdminEmail'] },
        { id: 'gwsSharedDrives', labelKey: 'dashboardPage.analyzeGWSSharedDrivesButton', servicePath: 'drive/shared-drives', analysisType: 'Google Workspace Shared Drives', requiredParams: ['gwsCustomerId', 'gwsAdminEmail'] },
      ]
    }
  };

  return (
    <div className="dashboard-page" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <Title order={1} ta="center" mb="xl">{t('dashboardPage.title')}</Title>

      {auth.user && (
        // Usar Paper da Mantine para o user-info para consistência
        <Paper withBorder p="md" mb="xl" shadow="xs" radius="md" style={{backgroundColor: "var(--mantine-color-gray-0)"}}>
          <Text>{t('dashboardPage.welcomeMessage', { userId: auth.user.user_id || auth.user.email || 'Usuário' })}</Text>
        </Paper>
      )}

      <MantineButton
        onClick={fetchAllAlerts}
        loading={isLoading && currentDisplayMode === 'all_alerts'}
        mb="xl"
        variant="filled"
      >
        {t('dashboardPage.fetchAllAlertsButton')}
      </MantineButton>

      <Tabs defaultValue="aws" variant="outline" radius="md">
        <Tabs.List grow>
          <Tabs.Tab value="aws">AWS</Tabs.Tab>
          <Tabs.Tab value="gcp">GCP</Tabs.Tab>
          <Tabs.Tab value="huawei">Huawei Cloud</Tabs.Tab>
          <Tabs.Tab value="azure">Azure</Tabs.Tab>
          <Tabs.Tab value="gws">Google Workspace</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="aws" pt="xs">
          <ProviderAnalysisSection
            providerId="aws"
            providerNameKey={providerConfigs.aws.providerNameKey}
            analysisButtons={providerConfigs.aws.analysisButtons}
            onAnalyze={handleAnalysis}
            isLoading={isLoading}
            currentAnalysisType={currentAnalysisType}
          />
        </Tabs.Panel>
        <Tabs.Panel value="gcp" pt="xs">
          <ProviderAnalysisSection
            providerId="gcp"
            providerNameKey={providerConfigs.gcp.providerNameKey}
            inputFields={providerConfigs.gcp.inputFields}
            analysisButtons={providerConfigs.gcp.analysisButtons}
            onAnalyze={handleAnalysis}
            isLoading={isLoading}
            currentAnalysisType={currentAnalysisType}
          />
        </Tabs.Panel>
        <Tabs.Panel value="huawei" pt="xs">
          <ProviderAnalysisSection
            providerId="huawei"
            providerNameKey={providerConfigs.huawei.providerNameKey}
            inputFields={providerConfigs.huawei.inputFields}
            analysisButtons={providerConfigs.huawei.analysisButtons}
            onAnalyze={handleAnalysis}
            isLoading={isLoading}
            currentAnalysisType={currentAnalysisType}
          />
        </Tabs.Panel>
        <Tabs.Panel value="azure" pt="xs">
          <ProviderAnalysisSection
            providerId="azure"
            providerNameKey={providerConfigs.azure.providerNameKey}
            inputFields={providerConfigs.azure.inputFields}
            analysisButtons={providerConfigs.azure.analysisButtons}
            onAnalyze={handleAnalysis}
            isLoading={isLoading}
            currentAnalysisType={currentAnalysisType}
          />
        </Tabs.Panel>
        <Tabs.Panel value="gws" pt="xs">
          <ProviderAnalysisSection
            providerId="googleworkspace"
            providerNameKey={providerConfigs.googleworkspace.providerNameKey}
            inputFields={providerConfigs.googleworkspace.inputFields}
            analysisButtons={providerConfigs.googleworkspace.analysisButtons}
            onAnalyze={handleAnalysis}
            isLoading={isLoading}
            currentAnalysisType={currentAnalysisType}
          />
        </Tabs.Panel>
      </Tabs>

      {isLoading && !alerts.length && <Text mt="md">{t('dashboardPage.loadingMessage', { type: currentDisplayMode === 'all_alerts' ? t('dashboardPage.allAlerts') : currentAnalysisType })}</Text>}
      {error && <Text mt="md" c="red" p="sm" style={{border: '1px solid red', borderRadius: '4px'}}>{error}</Text>}

      <AlertsTable
        alerts={alerts}
        title={
          currentDisplayMode === 'all_alerts'
            ? t('dashboardPage.allPersistedAlerts')
            : t('dashboardPage.alertsFoundFor', { type: currentAnalysisType || t('dashboardPage.unknownAnalysis') })
        }
      />
    </div>
  );
};

// Estilos básicos para a tabela (mantidos)
// Removidos pois agora estão em AlertsTable.tsx
// const tableHeaderStyle: React.CSSProperties = { ... };
// const tableCellStyle: React.CSSProperties = { ... };
// const evenRowStyle: React.CSSProperties = { ... };
// const oddRowStyle: React.CSSProperties = { ... };
// const getSeverityStyle = (severity: string): React.CSSProperties => { ... };

export default DashboardPage;
