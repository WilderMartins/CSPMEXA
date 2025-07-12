import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import ProviderAnalysisSection from '../components/Dashboard/ProviderAnalysisSection';
import AlertsTable, { Alert as AlertType } from '../components/Dashboard/AlertsTable'; // Renomeado Alert para AlertType
import { Tabs, Button as MantineButton, Title, Paper, Text, Alert as MantineAlert } from '@mantine/core'; // Adicionado MantineAlert
import { IconAlertCircle } from '@tabler/icons-react'; // Ícone para o MantineAlert

const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const auth = useAuth();

  // --- Estados do Componente ---
  const [alerts, setAlerts] = useState<AlertType[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [userInfo, setUserInfo] = useState<any>(null); // Adicionado da branch 'feature'
  const [currentDisplayMode, setCurrentDisplayMode] = useState<'all_alerts' | 'analysis_result'>('all_alerts'); [cite: 8]
  const [currentAnalysisType, setCurrentAnalysisType] = useState<string | null>(null); [cite: 8]

  // Estados para IDs dos provedores
  const [gcpProjectId, setGcpProjectId] = useState<string>('');
  const [huaweiProjectId, setHuaweiProjectId] = useState<string>('');
  const [huaweiRegionId, setHuaweiRegionId] = useState<string>(''); [cite: 13]
  const [huaweiDomainId, setHuaweiDomainId] = useState<string>(''); [cite: 13]
  const [azureSubscriptionId, setAzureSubscriptionId] = useState<string>(''); [cite: 13]
  const [googleWorkspaceCustomerId, setGoogleWorkspaceCustomerId] = useState<string>('my_customer'); [cite: 13]
  const [googleWorkspaceAdminEmail, setGoogleWorkspaceAdminEmail] = useState<string>(''); [cite: 14]

  // --- Lógica de Permissões (da branch 'feature') ---
  const ROLES_HIERARCHY = { [cite: 9]
    User: 1,
    TechnicalLead: 2,
    Manager: 3,
    Administrator: 4,
    SuperAdministrator: 5,
  };

  const hasPermission = (requiredRole: keyof typeof ROLES_HIERARCHY) => { [cite: 10]
    if (!auth.user || !auth.user.role) {
      return false;
    }
    const userLevel = ROLES_HIERARCHY[auth.user.role as keyof typeof ROLES_HIERARCHY] || 0;
    const requiredLevel = ROLES_HIERARCHY[requiredRole];
    return userLevel >= requiredLevel; [cite: 12]
  };

  // --- Funções de API ---
  const apiClient = useMemo(() => { [cite: 15]
    return axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
      headers: { 'Authorization': `Bearer ${auth.token}` }
    });
  }, [auth.token]);

  const fetchAllAlerts = async () => { [cite: 16]
    if (!auth.isAuthenticated) return;
    setIsLoading(true);
    setError(null);
    setAlerts([]);
    setCurrentDisplayMode('all_alerts');
    setCurrentAnalysisType(null);
    try { [cite: 17]
      const response = await apiClient.get<Alert[]>('/alerts?limit=100&sort_by=last_seen_at&sort_order=desc'); [cite: 17]
      setAlerts(response.data || []); [cite: 18]
      if (response.data.length === 0) setError(t('dashboardPage.noAlertsFound')); [cite: 18]
    } catch (err: any) { [cite: 19]
      const errorMessage = err.response?.data?.detail || err.message || t('dashboardPage.errorFetchingAlerts'); [cite: 20]
      setError(t('dashboardPage.errorFetchingAllAlerts', { error: errorMessage })); [cite: 20]
    } finally { [cite: 21]
      setIsLoading(false); [cite: 21]
    }
  };

  const handleAnalysis = async ( [cite: 23]
    provider: 'aws' | 'gcp' | 'huawei' | 'azure' | 'googleworkspace',
    servicePath: string,
    analysisType: string,
    idParams?: Record<string, string | undefined>
  ) => {
    setIsLoading(true); [cite: 23]
    setError(null); [cite: 24]
    setAlerts([]); [cite: 24]
    setCurrentDisplayMode('analysis_result'); [cite: 24]
    setCurrentAnalysisType(analysisType); [cite: 24]

    let url = `/analyze/${provider}/${servicePath}`;
    const queryParams = new URLSearchParams();

    // Lógica de parâmetros para cada provedor
    if (provider === 'gcp') {
      if (idParams?.projectId) {
        queryParams.append('project_id', idParams.projectId);
      } else {
        setError(t('dashboardPage.gcpProjectIdRequired'));
        setIsLoading(false);
        return;
      }
      // Adicionar location para GKE se necessário e fornecido em idParams
      if (servicePath.startsWith('gke/') && idParams?.gcpLocation) {
        queryParams.append('location', idParams.gcpLocation);
      } else if (servicePath.startsWith('gke/')) {
        queryParams.append('location', '-'); // Default para todas as localizações
      }
    } else if (provider === 'azure') {
      if (idParams?.subscriptionId) {
        queryParams.append('subscription_id', idParams.subscriptionId);
      } else {
        setError(t('dashboardPage.azureSubscriptionIdRequired'));
        setIsLoading(false);
        return;
      }
    } else if (provider === 'huawei') {
      if (idParams?.projectId) queryParams.append('project_id', idParams.projectId);
      // Alguns endpoints Huawei (ex: IAM Users) podem usar domain_id em vez de project_id
      // e todos precisam de region_id.
      if (idParams?.regionId) {
        queryParams.append('region_id', idParams.regionId);
      } else {
        setError(t('dashboardPage.huaweiRegionIdRequired'));
        setIsLoading(false);
        return;
      }
      if (idParams?.domainId) queryParams.append('domain_id', idParams.domainId); // Opcional para alguns, mas pode ser necessário
    } else if (provider === 'googleworkspace') {
      if (idParams?.customerId) queryParams.append('customer_id', idParams.customerId);
      if (idParams?.adminEmail) queryParams.append('delegated_admin_email', idParams.adminEmail);
      // Adicionar application_name para auditlogs se necessário
      if (servicePath.includes('auditlogs') && idParams?.gwsApplicationName) {
        queryParams.append('application_name', idParams.gwsApplicationName);
      } else if (servicePath.includes('auditlogs') && !idParams?.gwsApplicationName) {
        // Definir um default ou exigir, dependendo da API de backend
        // Por enquanto, vamos assumir que pode ser opcional ou ter um default no backend se não fornecido
      }
    }
    // AWS não requer IDs na URL para os endpoints atuais, eles são pegos do ambiente/config do backend

    const fullUrl = `${url}${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;

    try {
      const response = await apiClient.post<Alert[]>(fullUrl, {});
      setAlerts(response.data || []); [cite: 34]
      if (response.data.length === 0) setError(t('dashboardPage.noNewAlertsForAnalysis', { type: analysisType })); [cite: 35]
    } catch (err: any) { [cite: 36]
      const errorMessage = err.response?.data?.detail || err.message || t('dashboardPage.errorFetchingAlerts'); [cite: 36]
      setError(t('dashboardPage.errorDuringAnalysis', { type: analysisType, provider: provider.toUpperCase(), error: errorMessage })); [cite: 36]
    } finally { [cite: 37]
      setIsLoading(false); [cite: 37]
    }
  };

  // Função para atualizar o status do alerta (da branch 'feature')
  const handleUpdateAlertStatus = async (alertId: number, newStatus: string) => { [cite: 38]
    if (!hasPermission('TechnicalLead')) {
      setError(t('dashboardPage.errorNoPermissionToChangeStatus')); [cite: 38]
      return; [cite: 39]
    }
    setIsLoading(true);
    setError(null); [cite: 39]
    try { [cite: 40]
      const response = await apiClient.patch(`/alerts/${alertId}/status?new_status=${newStatus}`); [cite: 40]
      setAlerts(prevAlerts => [cite: 41]
        prevAlerts.map(alert => [cite: 41]
          alert.id === alertId ? { ...alert, status: response.data.status, updated_at: response.data.updated_at } : alert [cite: 41]
        ) [cite: 41]
      );
    } catch (err: any) { [cite: 43]
      const errorMessage = err.response?.data?.detail || err.message || t('dashboardPage.errorUpdatingStatus'); [cite: 44]
      setError(t('dashboardPage.errorUpdatingAlertStatus', { alertId, error: errorMessage })); [cite: 44]
    } finally { [cite: 45]
      setIsLoading(false); [cite: 45]
    }
  };

  // --- Efeitos ---
  useEffect(() => { [cite: 22]
    if (auth.isAuthenticated) {
      setUserInfo(auth.user); // Garante que userInfo tenha os dados do usuário logado
      fetchAllAlerts(); [cite: 22]
    }
  }, [auth.isAuthenticated, auth.user]);

  // --- Configuração da UI (da branch 'main') ---
  // TODO: Adicionar chaves de tradução para os novos placeholders e labels
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
        { id: 'gcpProjectId', name: 'projectId', labelKey: 'dashboardPage.gcpProjectIdLabel', placeholderKey: 'dashboardPage.gcpProjectIdPlaceholder', value: gcpProjectId, setter: setGcpProjectId }
        // Adicionar campo para gcpLocation se quisermos que seja configurável para GKE
      ],
      analysisButtons: [
        { id: 'gcpStorage', labelKey: 'dashboardPage.analyzeGCPStorageButton', servicePath: 'storage/buckets', analysisType: 'GCP Storage Buckets', requiredParams: ['projectId'] },
        { id: 'gcpComputeInstances', labelKey: 'dashboardPage.analyzeGCPInstancesButton', servicePath: 'compute/instances', analysisType: 'GCP Compute Instances', requiredParams: ['projectId'] },
        { id: 'gcpFirewalls', labelKey: 'dashboardPage.analyzeGCPFirewallsButton', servicePath: 'compute/firewalls', analysisType: 'GCP Compute Firewalls', requiredParams: ['projectId'] },
        { id: 'gcpIam', labelKey: 'dashboardPage.analyzeGCPIAMButton', servicePath: 'iam/project-policies', analysisType: 'GCP Project IAM', requiredParams: ['projectId'] },
        { id: 'gcpGke', labelKey: 'dashboardPage.analyzeGKEClustersButton', servicePath: 'gke/clusters', analysisType: 'GCP GKE Clusters', requiredParams: ['projectId'] }, // Adicionar gcpLocation como opcional aqui
      ]
    },
    huawei: {
      providerNameKey: 'dashboardPage.huaweiAnalysisTitle',
      inputFields: [
        { id: 'huaweiProjectIdInput', name: 'projectId', labelKey: 'dashboardPage.huaweiProjectIdLabel', placeholderKey: 'dashboardPage.huaweiProjectIdPlaceholder', value: huaweiProjectId, setter: setHuaweiProjectId },
        { id: 'huaweiRegionIdInput', name: 'regionId', labelKey: 'dashboardPage.huaweiRegionIdLabel', placeholderKey: 'dashboardPage.huaweiRegionIdPlaceholder', value: huaweiRegionId, setter: setHuaweiRegionId },
        { id: 'huaweiDomainIdInput', name: 'domainId', labelKey: 'dashboardPage.huaweiDomainIdLabel', placeholderKey: 'dashboardPage.huaweiDomainIdPlaceholder', value: huaweiDomainId, setter: setHuaweiDomainId, isOptional: true }
      ],
      analysisButtons: [
        { id: 'huaweiObs', labelKey: 'dashboardPage.analyzeHuaweiOBSButton', servicePath: 'obs/buckets', analysisType: 'Huawei OBS Buckets', requiredParams: ['projectId', 'regionId'] },
        { id: 'huaweiEcs', labelKey: 'dashboardPage.analyzeHuaweiECSButton', servicePath: 'ecs/instances', analysisType: 'Huawei ECS Instances', requiredParams: ['projectId', 'regionId'] },
        { id: 'huaweiSgs', labelKey: 'dashboardPage.analyzeHuaweiSGsButton', servicePath: 'vpc/security-groups', analysisType: 'Huawei VPC SGs', requiredParams: ['projectId', 'regionId'] },
        { id: 'huaweiIamUsers', labelKey: 'dashboardPage.analyzeHuaweiIAMUsersButton', servicePath: 'iam/users', analysisType: 'Huawei IAM Users', requiredParams: ['regionId'] }, // projectId ou domainId podem ser usados
      ]
    },
    azure: {
      providerNameKey: 'dashboardPage.azureAnalysisTitle',
      inputFields: [
        { id: 'azureSubId', name: 'subscriptionId', labelKey: 'dashboardPage.azureSubscriptionIdLabel', placeholderKey: 'dashboardPage.azureSubscriptionIdPlaceholder', value: azureSubscriptionId, setter: setAzureSubscriptionId }
      ],
      analysisButtons: [
        { id: 'azureVms', labelKey: 'dashboardPage.analyzeAzureVMsButton', servicePath: 'virtualmachines', analysisType: 'Azure Virtual Machines', requiredParams: ['subscriptionId'] },
        { id: 'azureStorage', labelKey: 'dashboardPage.analyzeAzureStorageButton', servicePath: 'storageaccounts', analysisType: 'Azure Storage Accounts', requiredParams: ['subscriptionId'] },
      ]
    },
    googleworkspace: {
      providerNameKey: 'dashboardPage.gwsAnalysisTitle',
      inputFields: [
        { id: 'gwsCustomerId', name: 'customerId', labelKey: 'dashboardPage.gwsCustomerIdLabel', placeholderKey: 'dashboardPage.gwsCustomerIdPlaceholder', value: googleWorkspaceCustomerId, setter: setGoogleWorkspaceCustomerId, isOptional: true },
        { id: 'gwsAdminEmail', name: 'adminEmail', labelKey: 'dashboardPage.gwsAdminEmailLabel', placeholderKey: 'dashboardPage.gwsAdminEmailPlaceholder', value: googleWorkspaceAdminEmail, setter: setGoogleWorkspaceAdminEmail, isOptional: true },
        // Adicionar campo para gwsApplicationName se quisermos que seja configurável para AuditLogs
      ],
      analysisButtons: [
        { id: 'gwsUsers', labelKey: 'dashboardPage.analyzeGWSUsersButton', servicePath: 'users', analysisType: 'Google Workspace Users' },
        { id: 'gwsSharedDrives', labelKey: 'dashboardPage.analyzeGWSSharedDrivesButton', servicePath: 'drive/shared-drives', analysisType: 'Google Workspace Shared Drives' },
        // Adicionar botão para GWS AuditLogs, passando gwsApplicationName
      ]
    }
  };

  // --- Renderização ---
  return ( [cite: 111]
    <div className="dashboard-page" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <Title order={1} ta="center" mb="xl">{t('dashboardPage.title')}</Title>

      {userInfo && (
        <Paper withBorder p="md" mb="xl" shadow="xs" radius="md" style={{backgroundColor: "var(--mantine-color-gray-0)"}}>
          <Text>{t('dashboardPage.welcomeMessage', { userId: userInfo.user_id || userInfo.email || 'Usuário' })}</Text>
        </Paper>
      )}

      <MantineButton [cite: 112]
        onClick={fetchAllAlerts} [cite: 112]
        loading={isLoading && currentDisplayMode === 'all_alerts'} [cite: 112]
        mb="xl" [cite: 112]
        variant="filled" [cite: 112]
      >
        {t('dashboardPage.fetchAllAlertsButton')} [cite: 112]
      </MantineButton>

      <Tabs defaultValue="aws" variant="outline" radius="md"> [cite: 112]
        <Tabs.List grow>
          <Tabs.Tab value="aws">AWS</Tabs.Tab> [cite: 112]
          <Tabs.Tab value="gcp">GCP</Tabs.Tab> [cite: 112]
          <Tabs.Tab value="huawei">Huawei Cloud</Tabs.Tab> [cite: 113]
          <Tabs.Tab value="azure">Azure</Tabs.Tab> [cite: 113]
          <Tabs.Tab value="gws">Google Workspace</Tabs.Tab> [cite: 113]
        </Tabs.List>

        <Tabs.Panel value="aws" pt="xs"> [cite: 114]
          <ProviderAnalysisSection
            providerId="aws"
            providerNameKey={providerConfigs.aws.providerNameKey}
            analysisButtons={providerConfigs.aws.analysisButtons}
            onAnalyze={handleAnalysis} [cite: 114]
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
            onAnalyze={(provider, service, type, buttonParams) => handleAnalysis(
              provider,
              service,
              type,
              {
                projectId: gcpProjectId,
                // gcpLocation: gcpLocation, // Descomentar se adicionar input para location
              }
            )}
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
            onAnalyze={(provider, service, type, buttonParams) => handleAnalysis(
              provider,
              service,
              type,
              {
                projectId: huaweiProjectId,
                regionId: huaweiRegionId,
                domainId: huaweiDomainId,
              }
            )}
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
            onAnalyze={(provider, service, type, buttonParams) => handleAnalysis(
              provider,
              service,
              type,
              {
                subscriptionId: azureSubscriptionId,
              }
            )}
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
            onAnalyze={(provider, service, type, buttonParams) => handleAnalysis(
              provider,
              service,
              type,
              {
                customerId: googleWorkspaceCustomerId,
                adminEmail: googleWorkspaceAdminEmail,
                // gwsApplicationName: gwsApplicationName, // Descomentar se adicionar input/select para app name
              }
            )}
            isLoading={isLoading}
            currentAnalysisType={currentAnalysisType}
          />
        </Tabs.Panel>
      </Tabs>

      {/* Exibição de Loading e Erro */}
      {isLoading && !alerts.length && <Text mt="md">{t('dashboardPage.loadingMessage', { type: currentDisplayMode === 'all_alerts' ? t('dashboardPage.allAlerts') : currentAnalysisType })}</Text>}
      {error && (
        <MantineAlert
          icon={<IconAlertCircle size="1rem" />}
          title={t('dashboardPage.errorTitle', 'Erro')}
          color="red"
          withCloseButton
          onClose={() => setError(null)}
          mt="md"
        >
          {error}
        </MantineAlert>
      )}

      {/* Tabela de Alertas integrada com as novas funcionalidades */}
      <AlertsTable
        alerts={alerts as AlertType[]}
        onUpdateStatus={handleUpdateAlertStatus} // Prop para a função de update
        canUpdateStatus={hasPermission('TechnicalLead')} // Prop para verificar permissão
        title={ [cite: 121]
          currentDisplayMode === 'all_alerts'
            ? t('dashboardPage.allPersistedAlerts') [cite: 121]
            : t('dashboardPage.alertsFoundFor', { type: currentAnalysisType || t('dashboardPage.unknownAnalysis') }) [cite: 121]
        }
      />
    </div>
  );
};

export default DashboardPage; [cite: 125]