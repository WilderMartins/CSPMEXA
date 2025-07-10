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
  const { t } = useTranslation(); // Hook de tradução

  const apiClient = axios.create({
    baseURL: '', // O proxy do Vite cuidará do redirecionamento para /api/v1
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

  const handleAnalysis = async (servicePath: string, analysisType: string) => {
    setIsLoading(true);
    setError(null);
    setAlerts([]); // Limpa alertas anteriores antes de nova análise
    setCurrentAnalysisType(analysisType);
    try {
      // O payload vazio {} é importante para POST se não houver corpo, mas a API espera.
      const response = await apiClient.post(`/api/v1/analyze/aws/${servicePath}`, {});
      setAlerts(response.data || []);
      if (response.data.length === 0) {
        setError(t('dashboardPage.noAlertsFor', { type: analysisType }));
      }
    } catch (err: any) {
      console.error(`Erro ao analisar ${analysisType}:`, err);
      const errorMessage = err.response?.data?.detail || err.message || t('dashboardPage.errorFetchingAlerts');
      setError(t('dashboardPage.errorDuringAnalysis', { type: analysisType, error: errorMessage }));
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

      <div className="analysis-buttons" style={{ marginBottom: '20px' }}>
        <button onClick={() => handleAnalysis('s3', 'S3 Buckets')} disabled={isLoading}>
          {isLoading && currentAnalysisType === 'S3 Buckets' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeS3Button')}
        </button>
        <button onClick={() => handleAnalysis('ec2/instances', 'EC2 Instances')} disabled={isLoading} style={{ marginLeft: '10px' }}>
          {isLoading && currentAnalysisType === 'EC2 Instances' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeEC2InstancesButton')}
        </button>
        <button onClick={() => handleAnalysis('ec2/security-groups', 'EC2 Security Groups')} disabled={isLoading} style={{ marginLeft: '10px' }}>
          {isLoading && currentAnalysisType === 'EC2 Security Groups' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeEC2SGsButton')}
        </button>
        <button onClick={() => handleAnalysis('iam/users', 'IAM Users')} disabled={isLoading} style={{ marginLeft: '10px' }}>
          {isLoading && currentAnalysisType === 'IAM Users' ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeIAMUsersButton')}
        </button>
        {/* Adicionar botões para IAM Roles e IAM Policies quando prontos */}
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
