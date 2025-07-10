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

  const handleAnalysis = async (provider: 'aws' | 'gcp', servicePath: string, analysisType: string, projectId?: string) => {
    setIsLoading(true);
    setError(null);
    setAlerts([]);
    setCurrentAnalysisType(analysisType);

    let url = `/api/v1/analyze/${provider}/${servicePath}`;
    if (provider === 'gcp') {
      if (!projectId) {
        setError(t('dashboardPage.gcpProjectIdRequired'));
        setIsLoading(false);
        return;
      }
      url += `?project_id=${encodeURIComponent(projectId)}`;
    }

    try {
      const response = await apiClient.post(url, {}); // POST request, body is empty for now
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

      <div className="aws-analysis-section" style={{ marginBottom: '30px', padding: '15px', border: '1px solid #e0e0e0', borderRadius: '5px' }}>
        <h3>{t('dashboardPage.awsAnalysisTitle')}</h3>
        <div className="analysis-buttons" style={{ marginTop: '10px' }}>
          <button onClick={() => handleAnalysis('aws', 's3', 'AWS S3 Buckets')} disabled={isLoading}>
            {isLoading && currentAnalysisType === 'AWS S3 Buckets' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeS3Button')}
          </button>
          <button onClick={() => handleAnalysis('aws', 'ec2/instances', 'AWS EC2 Instances')} disabled={isLoading} style={{ marginLeft: '10px' }}>
            {isLoading && currentAnalysisType === 'AWS EC2 Instances' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeEC2InstancesButton')}
          </button>
          <button onClick={() => handleAnalysis('aws', 'ec2/security-groups', 'AWS EC2 Security Groups')} disabled={isLoading} style={{ marginLeft: '10px' }}>
            {isLoading && currentAnalysisType === 'AWS EC2 Security Groups' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeEC2SGsButton')}
          </button>
          <button onClick={() => handleAnalysis('aws', 'iam/users', 'AWS IAM Users')} disabled={isLoading} style={{ marginLeft: '10px' }}>
            {isLoading && currentAnalysisType === 'AWS IAM Users' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeIAMUsersButton')}
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
        <div className="analysis-buttons" style={{ marginTop: '10px' }}>
          <button onClick={() => handleAnalysis('gcp', 'storage/buckets', 'GCP Storage Buckets', gcpProjectId)} disabled={isLoading || !gcpProjectId}>
            {isLoading && currentAnalysisType === 'GCP Storage Buckets' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeGCPStorageButton')}
          </button>
          <button onClick={() => handleAnalysis('gcp', 'compute/instances', 'GCP Compute Instances', gcpProjectId)} disabled={isLoading || !gcpProjectId} style={{ marginLeft: '10px' }}>
            {isLoading && currentAnalysisType === 'GCP Compute Instances' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeGCPInstancesButton')}
          </button>
          <button onClick={() => handleAnalysis('gcp', 'compute/firewalls', 'GCP Compute Firewalls', gcpProjectId)} disabled={isLoading || !gcpProjectId} style={{ marginLeft: '10px' }}>
            {isLoading && currentAnalysisType === 'GCP Compute Firewalls' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeGCPFirewallsButton')}
          </button>
          <button onClick={() => handleAnalysis('gcp', 'iam/project-policies', 'GCP Project IAM', gcpProjectId)} disabled={isLoading || !gcpProjectId} style={{ marginLeft: '10px' }}>
            {isLoading && currentAnalysisType === 'GCP Project IAM' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeGCPIAMButton')}
          </button>
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
