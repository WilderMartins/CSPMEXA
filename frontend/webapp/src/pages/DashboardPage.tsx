import React, { useState, useEffect } from 'react';
import axios from 'axios'; // Para chamadas de API
import { useTranslation } from 'react-i18next'; // Importar hook

// Interface Alert atualizada para corresponder ao AlertSchema do backend (com campos do DB)
interface Alert {
  id: number; // ID numérico do banco de dados
  resource_id: string;
  resource_type: string;
  account_id?: string;
  region?: string;
  provider: string;
  severity: string; // Idealmente, usar o AlertSeverityEnum se importado
  title: string;
  description: string;
  policy_id: string;
  status: string; // Idealmente, usar o AlertStatusEnum se importado
  details?: Record<string, any>;
  recommendation?: string;
  created_at: string; // Data como string ISO
  updated_at: string;
  first_seen_at: string;
  last_seen_at: string;
}

const DashboardPage: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [userInfo, setUserInfo] = useState<any>(null);
  const { t } = useTranslation();

  // Estado para o GCP Project ID
  const [gcpProjectId, setGcpProjectId] = useState<string>('');

  // Estados para Huawei Cloud
  const [huaweiProjectId, setHuaweiProjectId] = useState<string>('');
  const [huaweiRegionId, setHuaweiRegionId] = useState<string>(''); // e.g., ap-southeast-1
  const [huaweiDomainId, setHuaweiDomainId] = useState<string>(''); // Para IAM Users

  // Estado para Azure Subscription ID
  const [azureSubscriptionId, setAzureSubscriptionId] = useState<string>('');

  // Estados para Google Workspace
  const [googleWorkspaceCustomerId, setGoogleWorkspaceCustomerId] = useState<string>('my_customer'); // Default 'my_customer'
  const [googleWorkspaceAdminEmail, setGoogleWorkspaceAdminEmail] = useState<string>('');

  const apiClient = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('authToken')}`
    }
  });

  // Função para buscar todos os alertas persistidos
  const fetchAllAlerts = async () => {
    setIsLoading(true);
    setError(null);
    setAlerts([]);
    setCurrentDisplayMode('all_alerts');
    setCurrentAnalysisType(null); // Limpa o tipo de análise específica

    try {
      // Chama o novo endpoint GET /alerts do gateway
      const response = await apiClient.get('/alerts?limit=100&sort_by=last_seen_at&sort_order=desc');
      setAlerts(response.data || []);
      if (response.data.length === 0) {
        setError(t('dashboardPage.noAlertsFound'));
      }
    } catch (err: any) {
      console.error("Erro ao buscar todos os alertas:", err);
      const errorMessage = err.response?.data?.detail || err.message || t('dashboardPage.errorFetchingAlerts');
      setError(t('dashboardPage.errorFetchingAllAlerts', { error: errorMessage }));
    } finally {
      setIsLoading(false);
    }
  };

  // Buscar dados do usuário e todos os alertas ao carregar o dashboard
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        // Não é necessário esperar fetchUserInfo para chamar fetchAllAlerts
        apiClient.get('/users/me').then(response => {
          setUserInfo(response.data);
        }).catch(err => {
          console.error("Erro ao buscar informações do usuário:", err);
        });

        fetchAllAlerts(); // Carrega todos os alertas ao iniciar
      } catch (err) {
        // Erros já são tratados dentro de fetchUserInfo e fetchAllAlerts
      }
    };
    fetchInitialData();
  }, []); // Executa apenas uma vez ao montar


  const handleAnalysis = async (
    provider: 'aws' | 'gcp' | 'huawei' | 'azure' | 'googleworkspace',
    servicePath: string,
    analysisType: string,
    idParams?: {
      projectId?: string;
      regionId?: string;
      domainId?: string;
      subscriptionId?: string;
      gwsCustomerId?: string;
      gwsAdminEmail?: string;
    }
  ) => {
    setIsLoading(true);
    setError(null);
    setAlerts([]); // Limpa alertas anteriores
    setCurrentDisplayMode('analysis_result'); // Muda para modo de resultado de análise
    setCurrentAnalysisType(analysisType);

    let url = `/analyze/${provider}/${servicePath}`; // URL relativa ao baseURL do apiClient
    const queryParams = new URLSearchParams();

    // Lógica de parâmetros (mantida, mas URL base é tratada pelo apiClient)
    if (provider === 'gcp') {
      if (!idParams?.projectId) {
        setError(t('dashboardPage.gcpProjectIdRequired')); setIsLoading(false); return;
      }
      queryParams.append('project_id', idParams.projectId);
    } else if (provider === 'huawei') {
      if (!idParams?.projectId && servicePath !== 'iam/users') {
        setError(t('dashboardPage.huaweiProjectIdRequired')); setIsLoading(false); return;
      }
      if (!idParams?.regionId) {
        setError(t('dashboardPage.huaweiRegionIdRequired')); setIsLoading(false); return;
      }
      if (idParams.projectId) queryParams.append('project_id', idParams.projectId);
      queryParams.append('region_id', idParams.regionId);
      if (servicePath === 'iam/users' && idParams.domainId) {
        queryParams.append('domain_id', idParams.domainId);
      }
    } else if (provider === 'azure') {
      if (!idParams?.subscriptionId) {
        setError(t('dashboardPage.azureSubscriptionIdRequired')); setIsLoading(false); return;
      }
      queryParams.append('subscription_id', idParams.subscriptionId);
    } else if (provider === 'googleworkspace') {
      if (idParams?.gwsCustomerId) queryParams.append('customer_id', idParams.gwsCustomerId);
      if (idParams?.gwsAdminEmail) queryParams.append('delegated_admin_email', idParams.gwsAdminEmail);
    }

    const queryString = queryParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }

    try {
      // A resposta de /analyze agora também é uma lista de Alertas persistidos
      const response = await apiClient.post(url, {});
      setAlerts(response.data || []);
      if (response.data.length === 0) {
        setError(t('dashboardPage.noNewAlertsForAnalysis', { type: analysisType }));
      }
    } catch (err: any) {
      console.error(`Erro ao analisar ${analysisType} (${provider}):`, err);
      const errorMessage = err.response?.data?.detail || err.message || t('dashboardPage.errorFetchingAlerts');
      setError(t('dashboardPage.errorDuringAnalysis', { type: analysisType, provider: provider.toUpperCase(), error: errorMessage }));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="dashboard-page">
      <h2>{t('dashboardPage.title')}</h2>
      {userInfo && (
        <div className="user-info" style={{ marginBottom: '20px', padding: '10px', border: '1px solid #ccc', borderRadius: '4px' }}>
          <p>{t('dashboardPage.welcomeMessage', { userId: userInfo.user_id || userInfo.email || 'Usuário' })}</p>
        </div>
      )}

      {/* Botão para recarregar todos os alertas */}
      <div style={{ marginBottom: '20px' }}>
        <button onClick={fetchAllAlerts} disabled={isLoading}>
          {isLoading && currentDisplayMode === 'all_alerts' ? t('dashboardPage.loadingAllAlerts') : t('dashboardPage.fetchAllAlertsButton')}
        </button>
      </div>


      {/* Provider Analysis Sections Wrapper (igual ao anterior) */}
      <div className="provider-sections-wrapper" style={{ display: 'flex', flexWrap: 'wrap', gap: '20px' }}>
        {/* AWS Analysis Section */}
        <div className="aws-analysis-section provider-section" style={{ marginBottom: '30px', padding: '15px', border: '1px solid #e0e0e0', borderRadius: '5px', flexBasis: 'calc(50% - 10px)' }}>
          <h3>{t('dashboardPage.awsAnalysisTitle')}</h3>
          <div className="analysis-buttons" style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
            <button onClick={() => handleAnalysis('aws', 's3', 'AWS S3 Buckets')} disabled={isLoading}>
              {isLoading && currentAnalysisType === 'AWS S3 Buckets' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeS3Button')}
            </button>
            <button onClick={() => handleAnalysis('aws', 'ec2/instances', 'AWS EC2 Instances')} disabled={isLoading}>
              {isLoading && currentAnalysisType === 'AWS EC2 Instances' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeEC2InstancesButton')}
            </button>
            <button onClick={() => handleAnalysis('aws', 'ec2/security-groups', 'AWS EC2 Security Groups')} disabled={isLoading}>
              {isLoading && currentAnalysisType === 'AWS EC2 Security Groups' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeEC2SGsButton')}
            </button>
            <button onClick={() => handleAnalysis('aws', 'iam/users', 'AWS IAM Users')} disabled={isLoading}>
              {isLoading && currentAnalysisType === 'AWS IAM Users' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeIAMUsersButton')}
            </button>
            <button onClick={() => handleAnalysis('aws', 'rds/instances', 'AWS RDS Instances')} disabled={isLoading}>
              {isLoading && currentAnalysisType === 'AWS RDS Instances' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeRDSInstancesButton')}
            </button>
          </div>
        </div>

        {/* GCP Analysis Section */}
        <div className="gcp-analysis-section provider-section" style={{ marginBottom: '30px', padding: '15px', border: '1px solid #e0e0e0', borderRadius: '5px', flexBasis: 'calc(50% - 10px)' }}>
          <h3>{t('dashboardPage.gcpAnalysisTitle')}</h3>
          <div style={{ marginBottom: '10px' }}>
            <label htmlFor="gcpProjectId" style={{ marginRight: '10px' }}>{t('dashboardPage.gcpProjectIdLabel')}:</label>
            <input
              type="text"
              id="gcpProjectId"
              value={gcpProjectId}
              onChange={(e) => setGcpProjectId(e.target.value)}
              placeholder={t('dashboardPage.gcpProjectIdPlaceholder')}
              style={{ padding: '5px', minWidth: '250px' }}
            />
          </div>
          <div className="analysis-buttons" style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
            <button onClick={() => handleAnalysis('gcp', 'storage/buckets', 'GCP Storage Buckets', { projectId: gcpProjectId })} disabled={isLoading || !gcpProjectId}>
              {isLoading && currentAnalysisType === 'GCP Storage Buckets' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeGCPStorageButton')}
            </button>
            <button onClick={() => handleAnalysis('gcp', 'compute/instances', 'GCP Compute Instances', { projectId: gcpProjectId })} disabled={isLoading || !gcpProjectId}>
              {isLoading && currentAnalysisType === 'GCP Compute Instances' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeGCPInstancesButton')}
            </button>
            <button onClick={() => handleAnalysis('gcp', 'compute/firewalls', 'GCP Compute Firewalls', { projectId: gcpProjectId })} disabled={isLoading || !gcpProjectId}>
              {isLoading && currentAnalysisType === 'GCP Compute Firewalls' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeGCPFirewallsButton')}
            </button>
            <button onClick={() => handleAnalysis('gcp', 'iam/project-policies', 'GCP Project IAM', { projectId: gcpProjectId })} disabled={isLoading || !gcpProjectId}>
              {isLoading && currentAnalysisType === 'GCP Project IAM' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeGCPIAMButton')}
            </button>
          </div>
        </div>

        {/* Huawei Cloud Analysis Section */}
        <div className="huawei-analysis-section provider-section" style={{ marginBottom: '30px', padding: '15px', border: '1px solid #e0e0e0', borderRadius: '5px', flexBasis: 'calc(50% - 10px)' }}>
          <h3>{t('dashboardPage.huaweiAnalysisTitle')}</h3>
          <div style={{ marginBottom: '10px', display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
            <div>
              <label htmlFor="huaweiProjectId" style={{ marginRight: '5px' }}>{t('dashboardPage.huaweiProjectIdLabel')}:</label>
              <input type="text" id="huaweiProjectId" value={huaweiProjectId} onChange={(e) => setHuaweiProjectId(e.target.value)} placeholder={t('dashboardPage.huaweiProjectIdPlaceholder')} style={{ padding: '5px' }}/>
            </div>
            <div>
              <label htmlFor="huaweiRegionId" style={{ marginRight: '5px' }}>{t('dashboardPage.huaweiRegionIdLabel')}:</label>
              <input type="text" id="huaweiRegionId" value={huaweiRegionId} onChange={(e) => setHuaweiRegionId(e.target.value)} placeholder={t('dashboardPage.huaweiRegionIdPlaceholder')} style={{ padding: '5px' }}/>
            </div>
            <div>
              <label htmlFor="huaweiDomainId" style={{ marginRight: '5px' }}>{t('dashboardPage.huaweiDomainIdLabel')}:</label>
              <input type="text" id="huaweiDomainId" value={huaweiDomainId} onChange={(e) => setHuaweiDomainId(e.target.value)} placeholder={t('dashboardPage.huaweiDomainIdPlaceholder')} style={{ padding: '5px' }}/>
            </div>
          </div>
          <div className="analysis-buttons" style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
            <button onClick={() => handleAnalysis('huawei', 'obs/buckets', 'Huawei OBS Buckets', { projectId: huaweiProjectId, regionId: huaweiRegionId })} disabled={isLoading || !huaweiProjectId || !huaweiRegionId}>
              {isLoading && currentAnalysisType === 'Huawei OBS Buckets' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeHuaweiOBSButton')}
            </button>
            <button onClick={() => handleAnalysis('huawei', 'ecs/instances', 'Huawei ECS Instances', { projectId: huaweiProjectId, regionId: huaweiRegionId })} disabled={isLoading || !huaweiProjectId || !huaweiRegionId}>
              {isLoading && currentAnalysisType === 'Huawei ECS Instances' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeHuaweiECSButton')}
            </button>
            <button onClick={() => handleAnalysis('huawei', 'vpc/security-groups', 'Huawei VPC SGs', { projectId: huaweiProjectId, regionId: huaweiRegionId })} disabled={isLoading || !huaweiProjectId || !huaweiRegionId}>
              {isLoading && currentAnalysisType === 'Huawei VPC SGs' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeHuaweiSGsButton')}
            </button>
            <button onClick={() => handleAnalysis('huawei', 'iam/users', 'Huawei IAM Users', { projectId: huaweiProjectId, regionId: huaweiRegionId, domainId: huaweiDomainId })} disabled={isLoading || !huaweiRegionId /* Domain ID é opcional, mas region é crucial para o client IAM */}>
              {isLoading && currentAnalysisType === 'Huawei IAM Users' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeHuaweiIAMButton')}
            </button>
          </div>
        </div>

        {/* Azure Analysis Section */}
        <div className="azure-analysis-section provider-section" style={{ marginBottom: '30px', padding: '15px', border: '1px solid #e0e0e0', borderRadius: '5px', flexBasis: 'calc(50% - 10px)' }}>
          <h3>{t('dashboardPage.azureAnalysisTitle')}</h3>
          <div style={{ marginBottom: '10px' }}>
            <label htmlFor="azureSubscriptionId" style={{ marginRight: '10px' }}>{t('dashboardPage.azureSubscriptionIdLabel')}:</label>
            <input
              type="text"
              id="azureSubscriptionId"
              value={azureSubscriptionId}
              onChange={(e) => setAzureSubscriptionId(e.target.value)}
              placeholder={t('dashboardPage.azureSubscriptionIdPlaceholder')}
              style={{ padding: '5px', minWidth: '250px' }}
            />
          </div>
          <div className="analysis-buttons" style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
            <button
              onClick={() => handleAnalysis('azure', 'virtualmachines', 'Azure Virtual Machines', { subscriptionId: azureSubscriptionId })}
              disabled={isLoading || !azureSubscriptionId}
            >
              {isLoading && currentAnalysisType === 'Azure Virtual Machines' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeAzureVMsButton')}
            </button>
            <button
              onClick={() => handleAnalysis('azure', 'storageaccounts', 'Azure Storage Accounts', { subscriptionId: azureSubscriptionId })}
              disabled={isLoading || !azureSubscriptionId}
            >
              {isLoading && currentAnalysisType === 'Azure Storage Accounts' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeAzureStorageButton')}
            </button>
          </div>
        </div>

        {/* Google Workspace Analysis Section */}
        <div className="gws-analysis-section provider-section" style={{ marginBottom: '30px', padding: '15px', border: '1px solid #e0e0e0', borderRadius: '5px', flexBasis: 'calc(50% - 10px)' }}>
          <h3>{t('dashboardPage.gwsAnalysisTitle')}</h3>
          <div style={{ marginBottom: '10px', display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
            <div>
              <label htmlFor="gwsCustomerId" style={{ marginRight: '5px' }}>{t('dashboardPage.gwsCustomerIdLabel')}:</label>
              <input
                type="text" id="gwsCustomerId"
                value={googleWorkspaceCustomerId}
                onChange={(e) => setGoogleWorkspaceCustomerId(e.target.value)}
                placeholder={t('dashboardPage.gwsCustomerIdPlaceholder')}
                style={{ padding: '5px' }}
              />
            </div>
            <div>
              <label htmlFor="gwsAdminEmail" style={{ marginRight: '5px' }}>{t('dashboardPage.gwsAdminEmailLabel')}:</label>
              <input
                type="email" id="gwsAdminEmail"
                value={googleWorkspaceAdminEmail}
                onChange={(e) => setGoogleWorkspaceAdminEmail(e.target.value)}
                placeholder={t('dashboardPage.gwsAdminEmailPlaceholder')}
                style={{ padding: '5px', minWidth: '250px' }}
              />
            </div>
          </div>
          <div className="analysis-buttons" style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
            <button
              onClick={() => handleAnalysis('googleworkspace', 'users', 'Google Workspace Users', { gwsCustomerId: googleWorkspaceCustomerId, gwsAdminEmail: googleWorkspaceAdminEmail })}
              disabled={isLoading || (!googleWorkspaceCustomerId && !googleWorkspaceAdminEmail) /* Pelo menos um deve ser informado ou backend ter defaults */}
            >
              {isLoading && currentAnalysisType === 'Google Workspace Users' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeGWSUsersButton')}
            </button>
            <button
              onClick={() => handleAnalysis('googleworkspace', 'drive/shared-drives', 'Google Workspace Shared Drives', { gwsCustomerId: googleWorkspaceCustomerId, gwsAdminEmail: googleWorkspaceAdminEmail })}
              disabled={isLoading || (!googleWorkspaceCustomerId && !googleWorkspaceAdminEmail)}
            >
              {isLoading && currentAnalysisType === 'Google Workspace Shared Drives' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeGWSSharedDrivesButton')}
            </button>
            {/* Adicionar botão para /drive/public-files se a coleta for robustecida */}
          </div>
        </div>

      </div> {/* End of provider-sections-wrapper */}

      {isLoading && <p>{t('dashboardPage.loadingMessage', { type: currentDisplayMode === 'all_alerts' ? t('dashboardPage.allAlerts') : currentAnalysisType })}</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}

      {alerts.length > 0 && (
        <div className="alerts-container">
          <h3>
            {currentDisplayMode === 'all_alerts'
              ? t('dashboardPage.allPersistedAlerts')
              : t('dashboardPage.alertsFoundFor', { type: currentAnalysisType })}
          </h3>
          <table className="alerts-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={tableHeaderStyle}>{t('alertItem.id')}</th>
                <th style={tableHeaderStyle}>{t('alertItem.provider')}</th>
                <th style={tableHeaderStyle}>{t('alertItem.severity')}</th>
                <th style={tableHeaderStyle}>{t('alertItem.title')}</th>
                <th style={tableHeaderStyle}>{t('alertItem.resource')}</th>
                <th style={tableHeaderStyle}>{t('alertItem.resourceType')}</th>
                 <th style={tableHeaderStyle}>{t('alertItem.status')}</th>
                <th style={tableHeaderStyle}>{t('alertItem.firstSeen')}</th>
                <th style={tableHeaderStyle}>{t('alertItem.lastSeen')}</th>
                {/* <th style={tableHeaderStyle}>{t('alertItem.description')}</th> */}
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert, index) => (
                <tr key={alert.id} style={index % 2 === 0 ? evenRowStyle : oddRowStyle}>
                  <td style={tableCellStyle}>{alert.id}</td>
                  <td style={tableCellStyle}>{alert.provider.toUpperCase()}</td>
                  <td style={getSeverityStyle(alert.severity)}>{alert.severity}</td>
                  <td style={tableCellStyle} title={alert.description}>{alert.title}</td>
                  <td style={tableCellStyle}>{alert.resource_id}</td>
                  <td style={tableCellStyle}>{alert.resource_type}</td>
                  <td style={tableCellStyle}>{alert.status}</td>
                  <td style={tableCellStyle}>{new Date(alert.first_seen_at).toLocaleString()}</td>
                  <td style={tableCellStyle}>{new Date(alert.last_seen_at).toLocaleString()}</td>
                  {/* <td style={tableCellStyle}>{alert.description}</td> */}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// Estilos básicos para a tabela (mantidos)
const tableHeaderStyle: React.CSSProperties = {
  border: '1px solid #ddd',
  padding: '8px',
  textAlign: 'left',
  backgroundColor: '#f2f2f2',
};

const tableCellStyle: React.CSSProperties = {
  border: '1px solid #ddd',
  padding: '8px',
  textAlign: 'left',
};

const evenRowStyle: React.CSSProperties = {
  backgroundColor: '#f9f9f9',
};

const oddRowStyle: React.CSSProperties = {
  backgroundColor: '#ffffff',
};

const getSeverityStyle = (severity: string): React.CSSProperties => {
  let color = 'inherit';
  if (severity === 'Critical') color = 'red';
  else if (severity === 'High') color = 'orange';
  else if (severity === 'Medium') color = '#DAA520'; // DarkGoldenRod
  return { ...tableCellStyle, color, fontWeight: 'bold' };
};

export default DashboardPage;
          </button>
        </div>
      </div>

      <div className="gcp-analysis-section" style={{ marginBottom: '30px', padding: '15px', border: '1px solid #e0e0e0', borderRadius: '5px' }}>
        <h3>{t('dashboardPage.gcpAnalysisTitle')}</h3>
        <div style={{ marginBottom: '10px' }}>
          <label htmlFor="gcpProjectId" style={{ marginRight: '10px' }}>{t('dashboardPage.gcpProjectIdLabel')}:</label>
          <input
            type="text"
            id="gcpProjectId"
            value={gcpProjectId}
            onChange={(e) => setGcpProjectId(e.target.value)}
            placeholder={t('dashboardPage.gcpProjectIdPlaceholder')}
            style={{ padding: '5px', minWidth: '250px' }}
          />
        </div>
        <div className="analysis-buttons" style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
          <button onClick={() => handleAnalysis('gcp', 'storage/buckets', 'GCP Storage Buckets', { projectId: gcpProjectId })} disabled={isLoading || !gcpProjectId}>
            {isLoading && currentAnalysisType === 'GCP Storage Buckets' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeGCPStorageButton')}
          </button>
          <button onClick={() => handleAnalysis('gcp', 'compute/instances', 'GCP Compute Instances', { projectId: gcpProjectId })} disabled={isLoading || !gcpProjectId}>
            {isLoading && currentAnalysisType === 'GCP Compute Instances' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeGCPInstancesButton')}
          </button>
          <button onClick={() => handleAnalysis('gcp', 'compute/firewalls', 'GCP Compute Firewalls', { projectId: gcpProjectId })} disabled={isLoading || !gcpProjectId}>
            {isLoading && currentAnalysisType === 'GCP Compute Firewalls' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeGCPFirewallsButton')}
          </button>
          <button onClick={() => handleAnalysis('gcp', 'iam/project-policies', 'GCP Project IAM', { projectId: gcpProjectId })} disabled={isLoading || !gcpProjectId}>
            {isLoading && currentAnalysisType === 'GCP Project IAM' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeGCPIAMButton')}
          </button>
        </div>
      </div>

      <div className="huawei-analysis-section" style={{ marginBottom: '30px', padding: '15px', border: '1px solid #e0e0e0', borderRadius: '5px' }}>
        <h3>{t('dashboardPage.huaweiAnalysisTitle')}</h3>
        <div style={{ marginBottom: '10px', display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
          <div>
            <label htmlFor="huaweiProjectId" style={{ marginRight: '5px' }}>{t('dashboardPage.huaweiProjectIdLabel')}:</label>
            <input type="text" id="huaweiProjectId" value={huaweiProjectId} onChange={(e) => setHuaweiProjectId(e.target.value)} placeholder={t('dashboardPage.huaweiProjectIdPlaceholder')} style={{ padding: '5px' }}/>
          </div>
          <div>
            <label htmlFor="huaweiRegionId" style={{ marginRight: '5px' }}>{t('dashboardPage.huaweiRegionIdLabel')}:</label>
            <input type="text" id="huaweiRegionId" value={huaweiRegionId} onChange={(e) => setHuaweiRegionId(e.target.value)} placeholder={t('dashboardPage.huaweiRegionIdPlaceholder')} style={{ padding: '5px' }}/>
          </div>
          <div>
            <label htmlFor="huaweiDomainId" style={{ marginRight: '5px' }}>{t('dashboardPage.huaweiDomainIdLabel')}:</label>
            <input type="text" id="huaweiDomainId" value={huaweiDomainId} onChange={(e) => setHuaweiDomainId(e.target.value)} placeholder={t('dashboardPage.huaweiDomainIdPlaceholder')} style={{ padding: '5px' }}/>
          </div>
        </div>
        <div className="analysis-buttons" style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
          <button onClick={() => handleAnalysis('huawei', 'obs/buckets', 'Huawei OBS Buckets', { projectId: huaweiProjectId, regionId: huaweiRegionId })} disabled={isLoading || !huaweiProjectId || !huaweiRegionId}>
            {isLoading && currentAnalysisType === 'Huawei OBS Buckets' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeHuaweiOBSButton')}
          </button>
          <button onClick={() => handleAnalysis('huawei', 'ecs/instances', 'Huawei ECS Instances', { projectId: huaweiProjectId, regionId: huaweiRegionId })} disabled={isLoading || !huaweiProjectId || !huaweiRegionId}>
            {isLoading && currentAnalysisType === 'Huawei ECS Instances' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeHuaweiECSButton')}
          </button>
          <button onClick={() => handleAnalysis('huawei', 'vpc/security-groups', 'Huawei VPC SGs', { projectId: huaweiProjectId, regionId: huaweiRegionId })} disabled={isLoading || !huaweiProjectId || !huaweiRegionId}>
            {isLoading && currentAnalysisType === 'Huawei VPC SGs' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeHuaweiSGsButton')}
          </button>
          <button onClick={() => handleAnalysis('huawei', 'iam/users', 'Huawei IAM Users', { projectId: huaweiProjectId, regionId: huaweiRegionId, domainId: huaweiDomainId })} disabled={isLoading || !huaweiRegionId /* Domain ID é opcional, mas region é crucial para o client IAM */}>
            {isLoading && currentAnalysisType === 'Huawei IAM Users' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeHuaweiIAMButton')}
          </button>
        </div>
      </div>

      {/* Seção de Análise Azure */}
      <div className="azure-analysis-section" style={{ marginBottom: '30px', padding: '15px', border: '1px solid #e0e0e0', borderRadius: '5px' }}>
        <h3>{t('dashboardPage.azureAnalysisTitle')}</h3>
        <div style={{ marginBottom: '10px' }}>
          <label htmlFor="azureSubscriptionId" style={{ marginRight: '10px' }}>{t('dashboardPage.azureSubscriptionIdLabel')}:</label>
          <input
            type="text"
            id="azureSubscriptionId"
            value={azureSubscriptionId}
            onChange={(e) => setAzureSubscriptionId(e.target.value)}
            placeholder={t('dashboardPage.azureSubscriptionIdPlaceholder')}
            style={{ padding: '5px', minWidth: '250px' }}
          />
        </div>
        <div className="analysis-buttons" style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
          <button
            onClick={() => handleAnalysis('azure', 'virtualmachines', 'Azure Virtual Machines', { subscriptionId: azureSubscriptionId })}
            disabled={isLoading || !azureSubscriptionId}
          >
            {isLoading && currentAnalysisType === 'Azure Virtual Machines' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeAzureVMsButton')}
          </button>
          <button
            onClick={() => handleAnalysis('azure', 'storageaccounts', 'Azure Storage Accounts', { subscriptionId: azureSubscriptionId })}
            disabled={isLoading || !azureSubscriptionId}
          >
            {isLoading && currentAnalysisType === 'Azure Storage Accounts' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeAzureStorageButton')}
          </button>
        </div>
      </div>

      {/* Seção de Análise Google Workspace */}
      <div className="gws-analysis-section" style={{ marginBottom: '30px', padding: '15px', border: '1px solid #e0e0e0', borderRadius: '5px' }}>
        <h3>{t('dashboardPage.gwsAnalysisTitle')}</h3>
        <div style={{ marginBottom: '10px', display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
          <div>
            <label htmlFor="gwsCustomerId" style={{ marginRight: '5px' }}>{t('dashboardPage.gwsCustomerIdLabel')}:</label>
            <input
              type="text" id="gwsCustomerId"
              value={googleWorkspaceCustomerId}
              onChange={(e) => setGoogleWorkspaceCustomerId(e.target.value)}
              placeholder={t('dashboardPage.gwsCustomerIdPlaceholder')}
              style={{ padding: '5px' }}
            />
          </div>
          <div>
            <label htmlFor="gwsAdminEmail" style={{ marginRight: '5px' }}>{t('dashboardPage.gwsAdminEmailLabel')}:</label>
            <input
              type="email" id="gwsAdminEmail"
              value={googleWorkspaceAdminEmail}
              onChange={(e) => setGoogleWorkspaceAdminEmail(e.target.value)}
              placeholder={t('dashboardPage.gwsAdminEmailPlaceholder')}
              style={{ padding: '5px', minWidth: '250px' }}
            />
          </div>
        </div>
        <div className="analysis-buttons" style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
          <button
            onClick={() => handleAnalysis('googleworkspace', 'users', 'Google Workspace Users', { gwsCustomerId: googleWorkspaceCustomerId, gwsAdminEmail: googleWorkspaceAdminEmail })}
            disabled={isLoading || (!googleWorkspaceCustomerId && !googleWorkspaceAdminEmail) /* Pelo menos um deve ser informado ou backend ter defaults */}
          >
            {isLoading && currentAnalysisType === 'Google Workspace Users' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeGWSUsersButton')}
          </button>
          {/* Adicionar botões para Drive, Gmail, etc. aqui no futuro */}
        </div>
      </div>

      {isLoading && <p>{t('dashboardPage.loadingMessage', { type: currentAnalysisType })}</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}

      {alerts.length > 0 && (
        <div className="alerts-container">
          <h3>{t('dashboardPage.alertsFoundFor', { type: currentAnalysisType })}</h3>
          <table className="alerts-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={tableHeaderStyle}>{t('alertItem.severity')}</th>
                <th style={tableHeaderStyle}>{t('alertItem.title')}</th>
                <th style={tableHeaderStyle}>{t('alertItem.resource')}</th>
                <th style={tableHeaderStyle}>{t('alertItem.resourceType')}</th>
                <th style={tableHeaderStyle}>{t('alertItem.description')}</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert, index) => (
                <tr key={alert.id || index} style={index % 2 === 0 ? evenRowStyle : oddRowStyle}>
                  <td style={getSeverityStyle(alert.severity)}>{alert.severity}</td>
                  <td style={tableCellStyle}>{alert.title}</td>
                  <td style={tableCellStyle}>{alert.resource_id}</td>
                  <td style={tableCellStyle}>{alert.resource_type}</td>
                  <td style={tableCellStyle}>{alert.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// Estilos básicos para a tabela (podem ser movidos para um arquivo CSS)
const tableHeaderStyle: React.CSSProperties = {
  border: '1px solid #ddd',
  padding: '8px',
  textAlign: 'left',
  backgroundColor: '#f2f2f2',
};

const tableCellStyle: React.CSSProperties = {
  border: '1px solid #ddd',
  padding: '8px',
  textAlign: 'left',
};

const evenRowStyle: React.CSSProperties = {
  backgroundColor: '#f9f9f9',
};

const oddRowStyle: React.CSSProperties = {
  backgroundColor: '#ffffff',
};

const getSeverityStyle = (severity: string): React.CSSProperties => {
  let color = 'inherit';
  if (severity === 'Critical') color = 'red';
  else if (severity === 'High') color = 'orange';
  else if (severity === 'Medium') color = '#DAA520'; // DarkGoldenRod
  return { ...tableCellStyle, color, fontWeight: 'bold' };
};

export default DashboardPage;
