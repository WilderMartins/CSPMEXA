import React, { useState, useEffect, useMemo } from 'react'; [cite: 1]
import axios from 'axios'; [cite: 1]
import { useTranslation } from 'react-i18next'; [cite: 1]
import { useAuth } from '../contexts/AuthContext'; [cite: 2]
import ProviderAnalysisSection from '../components/Dashboard/ProviderAnalysisSection'; [cite: 2]
import AlertsTable, { Alert } from '../components/Dashboard/AlertsTable'; [cite: 2]
import { Tabs, Button as MantineButton, Title, Paper, Text } from '@mantine/core'; [cite: 3]

const DashboardPage: React.FC = () => {
  const { t } = useTranslation(); [cite: 5]
  const auth = useAuth(); [cite: 6]

  // --- Estados do Componente ---
  const [alerts, setAlerts] = useState<Alert[]>([]); [cite: 6]
  const [isLoading, setIsLoading] = useState<boolean>(false); [cite: 6]
  const [error, setError] = useState<string | null>(null); [cite: 6, 7]
  const [userInfo, setUserInfo] = useState<any>(null); // Adicionado da branch 'feature' [cite: 7]
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
    
    // Lógica de parâmetros...
    if (provider === 'gcp' && idParams?.projectId) queryParams.append('project_id', idParams.projectId); [cite: 25]
    else if (provider === 'gcp' && !idParams?.projectId) { setError(t('dashboardPage.gcpProjectIdRequired')); setIsLoading(false); return; [cite: 25] }

    try { [cite: 33]
      const response = await apiClient.post<Alert[]>(url, {}); [cite: 33]
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
  const providerConfigs = { [cite: 103]
    aws: {
      providerNameKey: 'dashboardPage.awsAnalysisTitle',
      analysisButtons: [ [cite: 104]
        { id: 's3', labelKey: 'dashboardPage.analyzeS3Button', servicePath: 's3', analysisType: 'AWS S3 Buckets' }, [cite: 104]
        { id: 'ec2Instances', labelKey: 'dashboardPage.analyzeEC2InstancesButton', servicePath: 'ec2/instances', analysisType: 'AWS EC2 Instances' }, [cite: 104]
        { id: 'ec2Sgs', labelKey: 'dashboardPage.analyzeEC2SGsButton', servicePath: 'ec2/security-groups', analysisType: 'AWS EC2 Security Groups' }, [cite: 104]
        { id: 'iamUsers', labelKey: 'dashboardPage.analyzeIAMUsersButton', servicePath: 'iam/users', analysisType: 'AWS IAM Users' }, [cite: 104]
        { id: 'rdsInstances', labelKey: 'dashboardPage.analyzeRDSInstancesButton', servicePath: 'rds/instances', analysisType: 'AWS RDS Instances' }, [cite: 104]
      ]
    },
    gcp: { [cite: 105]
      providerNameKey: 'dashboardPage.gcpAnalysisTitle', [cite: 105]
      inputFields: [ [cite: 105]
        { id: 'projectId', labelKey: 'dashboardPage.gcpProjectIdLabel', placeholderKey: 'dashboardPage.gcpProjectIdPlaceholder', value: gcpProjectId, setter: setGcpProjectId } [cite: 105]
      ],
      analysisButtons: [ [cite: 105]
        { id: 'storage', labelKey: 'dashboardPage.analyzeGCPStorageButton', servicePath: 'storage/buckets', analysisType: 'GCP Storage Buckets', requiredParams: ['projectId'] }, [cite: 105]
        { id: 'computeInstances', labelKey: 'dashboardPage.analyzeGCPInstancesButton', servicePath: 'compute/instances', analysisType: 'GCP Compute Instances', requiredParams: ['projectId'] }, [cite: 105]
        { id: 'firewalls', labelKey: 'dashboardPage.analyzeGCPFirewallsButton', servicePath: 'compute/firewalls', analysisType: 'GCP Compute Firewalls', requiredParams: ['projectId'] }, [cite: 106]
        { id: 'iam', labelKey: 'dashboardPage.analyzeGCPIAMButton', servicePath: 'iam/project-policies', analysisType: 'GCP Project IAM', requiredParams: ['projectId'] }, [cite: 106]
        { id: 'gke', labelKey: 'dashboardPage.analyzeGKEClustersButton', servicePath: 'gke/clusters', analysisType: 'GCP GKE Clusters', requiredParams: ['projectId'] }, [cite: 106]
      ]
    },
    // Demais configurações (huawei, azure, googleworkspace) continuam aqui...
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
        <Tabs.Panel value="gcp" pt="xs"> [cite: 115]
           <ProviderAnalysisSection
            providerId="gcp"
            providerNameKey={providerConfigs.gcp.providerNameKey}
            inputFields={providerConfigs.gcp.inputFields} [cite: 115]
            analysisButtons={providerConfigs.gcp.analysisButtons}
            onAnalyze={(provider, service, type) => handleAnalysis(provider, service, type, { projectId: gcpProjectId })}
            isLoading={isLoading}
            currentAnalysisType={currentAnalysisType}
          />
        </Tabs.Panel>
        {/* Adicione os outros Tabs.Panel aqui, seguindo o modelo acima. */}
      </Tabs>

      {/* Exibição de Loading e Erro */}
      {isLoading && !alerts.length && <Text mt="md">{t('dashboardPage.loadingMessage', { type: currentDisplayMode === 'all_alerts' ? t('dashboardPage.allAlerts') : currentAnalysisType })}</Text>} [cite: 119, 120]
      {error && <Text mt="md" c="red" p="sm" style={{border: '1px solid red', borderRadius: '4px'}}>{error}</Text>} [cite: 120]

      {/* Tabela de Alertas integrada com as novas funcionalidades */}
      <AlertsTable [cite: 121]
        alerts={alerts} [cite: 121]
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