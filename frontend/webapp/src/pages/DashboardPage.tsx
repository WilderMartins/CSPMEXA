import React, { useState, useEffect } from 'react';
import axios from 'axios'; // Para chamadas de API
import { useTranslation } from 'react-i18next'; // Importar hook

interface Alert {
  id?: string;
  resource_id: string;
  resource_type: string;
  severity: string;
  title: string;
  description: string;
  // Adicionar outros campos do schema Alert se necessário
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
    baseURL: '',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('authToken')}`
    }
  });

  // Buscar dados do usuário ao carregar o dashboard
  useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        const response = await apiClient.get('/api/v1/users/me');
        setUserInfo(response.data);
      } catch (err) {
        console.error("Erro ao buscar informações do usuário:", err);
        // Poderia tratar erro de token inválido/expirado aqui, e deslogar o usuário
      }
    };
    fetchUserInfo();
  }, []);


  const [currentAnalysisType, setCurrentAnalysisType] = useState<string | null>(null);

  const handleAnalysis = async (
    provider: 'aws' | 'gcp' | 'huawei' | 'azure' | 'googleworkspace', // Adicionado 'googleworkspace'
    servicePath: string,
    analysisType: string,
    idParams?: {
      projectId?: string;
      regionId?: string;
      domainId?: string;
      subscriptionId?: string;
      gwsCustomerId?: string; // Para Google Workspace
      gwsAdminEmail?: string; // Para Google Workspace
    }
  ) => {
    setIsLoading(true);
    setError(null);
    setAlerts([]);
    setCurrentAnalysisType(analysisType);

    let url = `/api/v1/analyze/${provider}/${servicePath}`;
    const queryParams = new URLSearchParams();

    if (provider === 'gcp') {
      if (!idParams?.projectId) {
        setError(t('dashboardPage.gcpProjectIdRequired'));
        setIsLoading(false);
        return;
      }
      queryParams.append('project_id', idParams.projectId);
    } else if (provider === 'huawei') {
      if (!idParams?.projectId && servicePath !== 'iam/users') { // IAM users usa domain_id
        setError(t('dashboardPage.huaweiProjectIdRequired'));
        setIsLoading(false);
        return;
      }
      if (!idParams?.regionId) {
        setError(t('dashboardPage.huaweiRegionIdRequired'));
        setIsLoading(false);
        return;
      }
      if (idParams.projectId) queryParams.append('project_id', idParams.projectId);
      queryParams.append('region_id', idParams.regionId);
      if (servicePath === 'iam/users' && idParams.domainId) { // Domain ID é opcional mas preferido para IAM users
        queryParams.append('domain_id', idParams.domainId);
      } else if (servicePath === 'iam/users' && !idParams.domainId) {
        // Se domain_id não for fornecido para IAM users, o backend tentará usar variáveis de ambiente
        // ou o project_id como fallback, o que pode não ser o ideal mas permite a chamada.
        // Adicionar um aviso ou exigir domain_id para IAM é uma opção.
        // Por enquanto, permitimos a chamada. O backend logará um aviso se o domain_id não for claro.
      }
    } else if (provider === 'azure') {
      if (!idParams?.subscriptionId) {
        setError(t('dashboardPage.azureSubscriptionIdRequired')); // Adicionar esta chave de tradução
        setIsLoading(false);
        return;
      }
      queryParams.append('subscription_id', idParams.subscriptionId);
    } else if (provider === 'googleworkspace') {
      // customerId é opcional no backend (default 'my_customer'), mas adminEmail é crucial se não configurado no backend.
      // O frontend deve enviar ambos se o usuário os preencher.
      if (!idParams?.gwsAdminEmail && !idParams?.gwsCustomerId) { // Se ambos vazios, pode dar erro se backend não tiver defaults.
         // Relaxar essa checagem por agora, assumindo que o backend pode ter defaults ou o usuário sabe que precisa de um deles.
         // setError(t('dashboardPage.gwsAdminEmailRequired')); // Adicionar tradução
         // setIsLoading(false);
         // return;
      }
      if (idParams?.gwsCustomerId) {
        queryParams.append('customer_id', idParams.gwsCustomerId);
      }
      if (idParams?.gwsAdminEmail) {
        queryParams.append('delegated_admin_email', idParams.gwsAdminEmail);
      }
    }

    const queryString = queryParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }

    try {
      const response = await apiClient.post(url, {});
      setAlerts(response.data || []);
      if (response.data.length === 0) {
        setError(t('dashboardPage.noAlertsFor', { type: analysisType }));
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

      {/* Provider Analysis Sections Wrapper */}
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
            {/* Adicionar botões para Drive, Gmail, etc. aqui no futuro */}
          </div>
        </div>

      </div> {/* End of provider-sections-wrapper */}

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
