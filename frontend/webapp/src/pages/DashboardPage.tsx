import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import ProviderAnalysisSection from '../components/Dashboard/ProviderAnalysisSection';
import AlertsTable, { Alert } from '../components/Dashboard/AlertsTable'; // Importar AlertsTable e a interface Alert

// Simulação de componentes Tabs de uma biblioteca UI (mantido para estrutura da página)
const Tabs: React.FC<{ children: React.ReactNode, defaultValue?: string, style?: React.CSSProperties }> = ({ children, defaultValue, style }) => {
  const [activeTab, setActiveTab] = useState(defaultValue || '');
  const tabs = React.Children.toArray(children).filter(child => React.isValidElement(child) && child.props.value);
  useEffect(() => {
    if (!defaultValue && tabs.length > 0 && React.isValidElement(tabs[0])) {
      setActiveTab(tabs[0].props.value);
    }
  }, [defaultValue, tabs]);

  return (
    <div style={style}>
      <div style={{ display: 'flex', borderBottom: '1px solid #dee2e6', marginBottom: '1rem' }}>
        {tabs.map((child) => {
          if (!React.isValidElement(child)) return null;
          const { value, label } = child.props;
          return (
            <button
              key={value}
              onClick={() => setActiveTab(value)}
              style={{
                padding: '10px 15px', border: 'none',
                borderBottom: activeTab === value ? '2px solid #007bff' : '2px solid transparent',
                cursor: 'pointer', backgroundColor: 'transparent',
                fontWeight: activeTab === value ? 'bold' : 'normal',
                color: activeTab === value ? '#007bff' : '#495057', outline: 'none',
              }}
            >
              {label}
            </button>
          );
        })}
      </div>
      <div>
        {React.Children.map(children, child => React.isValidElement(child) && child.props.value === activeTab ? child : null)}
      </div>
    </div>
  );
};

const TabPanel: React.FC<{ children: React.ReactNode, value: string, label: string }> = ({ children }) => {
  return <>{children}</>;
};


const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const auth = useAuth();

  const [alerts, setAlerts] = useState<Alert[]>([]); // Usa a interface Alert importada
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
    <div className="dashboard-page" style={{ padding: '20px' }}>
      <h2 style={{ marginBottom: '20px' }}>{t('dashboardPage.title')}</h2>
      {auth.user && (
        <div className="user-info" style={{ marginBottom: '20px', padding: '10px', border: '1px solid #eee', borderRadius: '4px', backgroundColor: '#f9f9f9' }}>
          <p>{t('dashboardPage.welcomeMessage', { userId: auth.user.user_id || auth.user.email || 'Usuário' })}</p>
        </div>
      )}

      <div style={{ marginBottom: '20px' }}>
        <button
          onClick={fetchAllAlerts}
          disabled={isLoading && currentDisplayMode === 'all_alerts'}
          style={{padding: '10px 15px', border: 'none', borderRadius: '4px', backgroundColor: '#007bff', color: 'white', cursor: 'pointer'}}
        >
          {isLoading && currentDisplayMode === 'all_alerts' ? t('dashboardPage.loadingAllAlerts') : t('dashboardPage.fetchAllAlertsButton')}
        </button>
      </div>

      <Tabs defaultValue="aws" style={{ marginBottom: '30px' }}>
        <TabPanel value="aws" label="AWS">
          <ProviderAnalysisSection
            providerId="aws"
            providerNameKey={providerConfigs.aws.providerNameKey}
            analysisButtons={providerConfigs.aws.analysisButtons}
            onAnalyze={handleAnalysis}
            isLoading={isLoading}
            currentAnalysisType={currentAnalysisType}
          />
        </TabPanel>
        <TabPanel value="gcp" label="GCP">
          <ProviderAnalysisSection
            providerId="gcp"
            providerNameKey={providerConfigs.gcp.providerNameKey}
            inputFields={providerConfigs.gcp.inputFields}
            analysisButtons={providerConfigs.gcp.analysisButtons}
            onAnalyze={handleAnalysis}
            isLoading={isLoading}
            currentAnalysisType={currentAnalysisType}
          />
        </TabPanel>
        <TabPanel value="huawei" label="Huawei Cloud">
          <ProviderAnalysisSection
            providerId="huawei"
            providerNameKey={providerConfigs.huawei.providerNameKey}
            inputFields={providerConfigs.huawei.inputFields}
            analysisButtons={providerConfigs.huawei.analysisButtons}
            onAnalyze={handleAnalysis}
            isLoading={isLoading}
            currentAnalysisType={currentAnalysisType}
          />
        </TabPanel>
        <TabPanel value="azure" label="Azure">
          <ProviderAnalysisSection
            providerId="azure"
            providerNameKey={providerConfigs.azure.providerNameKey}
            inputFields={providerConfigs.azure.inputFields}
            analysisButtons={providerConfigs.azure.analysisButtons}
            onAnalyze={handleAnalysis}
            isLoading={isLoading}
            currentAnalysisType={currentAnalysisType}
          />
        </TabPanel>
        <TabPanel value="gws" label="Google Workspace">
          <ProviderAnalysisSection
            providerId="googleworkspace"
            providerNameKey={providerConfigs.googleworkspace.providerNameKey}
            inputFields={providerConfigs.googleworkspace.inputFields}
            analysisButtons={providerConfigs.googleworkspace.analysisButtons}
            onAnalyze={handleAnalysis}
            isLoading={isLoading}
            currentAnalysisType={currentAnalysisType}
          />
        </TabPanel>
      </Tabs>

      {isLoading && !alerts.length && <p>{t('dashboardPage.loadingMessage', { type: currentDisplayMode === 'all_alerts' ? t('dashboardPage.allAlerts') : currentAnalysisType })}</p>}
      {error && <p style={{ color: 'red', marginTop: '1rem', padding: '10px', border: '1px solid red', borderRadius: '4px' }}>{error}</p>}

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
