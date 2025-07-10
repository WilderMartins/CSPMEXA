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


  const handleAnalyzeS3 = async () => {
    setIsLoading(true);
    setError(null);
    setAlerts([]);
    try {
      const response = await apiClient.post('/api/v1/analyze/aws/s3', {});
      setAlerts(response.data || []);
      if (response.data.length === 0) {
        setError(t('dashboardPage.noAlerts'));
      }
    } catch (err: any) {
      console.error("Erro ao analisar S3:", err);
      setError(err.response?.data?.detail || err.message || t('dashboardPage.errorFetchingAlerts'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="dashboard-page-placeholder">
      <h2>{t('dashboardPage.title')}</h2>
      {userInfo && (
        <div style={{ marginBottom: '20px', padding: '10px', border: '1px solid #ccc', borderRadius: '4px' }}>
          <p>{t('dashboardPage.welcomeMessage', { userId: userInfo.user_id })}</p>
        </div>
      )}
      <button onClick={handleAnalyzeS3} disabled={isLoading}>
        {isLoading ? t('dashboardPage.analyzingButton') : t('dashboardPage.analyzeButton')}
      </button>

      {error && <p style={{ color: 'red' }}>{t('dashboardPage.errorFetchingAlerts')}: {error}</p>}

      {alerts.length > 0 && (
        <div className="alerts-container">
          <h3>{t('dashboardPage.alertsFound')}</h3>
          {alerts.map((alert, index) => (
            <div key={alert.id || index} className="alert-item">
              <h4>{alert.title}</h4>
              <p><strong>{t('alertItem.resource')}</strong> {alert.resource_id} ({alert.resource_type})</p>
              <p><strong>{t('alertItem.severity')}</strong> <span style={{color: alert.severity === 'Critical' ? 'red' : (alert.severity === 'High' ? 'orange' : 'inherit')}}>{alert.severity}</span></p>
              <p>{alert.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default DashboardPage;
