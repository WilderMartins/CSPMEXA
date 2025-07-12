import React, { useState, useEffect } from 'react';
// Supondo que exista um serviço de API para fazer chamadas
// import apiService from '../../services/api';

// Mock do serviço de API para desenvolvimento
const apiService = {
  get: async (path: string) => {
    console.log(`GET: ${path}`);
    if (path === '/admin/credentials') {
      return Promise.resolve([{ provider: 'aws', configured: true }]);
    }
    return Promise.resolve([]);
  },
  post: async (path: string, body: any) => {
    console.log(`POST: ${path}`, body);
    alert(`Credenciais para ${body.provider} salvas (simulação).`);
    return Promise.resolve({ status: 204 });
  },
  delete: async (path: string) => {
    console.log(`DELETE: ${path}`);
    alert(`Credenciais deletadas (simulação).`);
    return Promise.resolve({ status: 204 });
  },
};


const CredentialsPage: React.FC = () => {
  const [configuredProviders, setConfiguredProviders] = useState<any[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('aws');
  const [awsKeys, setAwsKeys] = useState({ aws_access_key_id: '', aws_secret_access_key: '' });
  const [azureKeys, setAzureKeys] = useState({ azure_client_id: '', azure_client_secret: '', azure_tenant_id: '', azure_subscription_id: '' });

  const fetchConfiguredProviders = async () => {
    try {
      const response = await apiService.get('/admin/credentials');
      setConfiguredProviders(response);
    } catch (error) {
      console.error('Erro ao buscar provedores configurados:', error);
    }
  };

  useEffect(() => {
    fetchConfiguredProviders();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const credentials = selectedProvider === 'aws' ? awsKeys : azureKeys;
    try {
      await apiService.post(`/admin/credentials/${selectedProvider}`, credentials);
      fetchConfiguredProviders(); // Atualiza a lista
    } catch (error) {
      console.error(`Erro ao salvar credenciais para ${selectedProvider}:`, error);
    }
  };

  const handleDelete = async (provider: string) => {
    if (window.confirm(`Tem certeza que deseja deletar as credenciais do ${provider}?`)) {
      try {
        await apiService.delete(`/admin/credentials/${provider}`);
        fetchConfiguredProviders(); // Atualiza a lista
      } catch (error) {
        console.error(`Erro ao deletar credenciais para ${provider}:`, error);
      }
    }
  };

  const renderForm = () => {
    if (selectedProvider === 'aws') {
      return (
        <>
          <div className="form-group">
            <label>AWS Access Key ID</label>
            <input type="text" value={awsKeys.aws_access_key_id} onChange={(e) => setAwsKeys({ ...awsKeys, aws_access_key_id: e.target.value })} />
          </div>
          <div className="form-group">
            <label>AWS Secret Access Key</label>
            <input type="password" value={awsKeys.aws_secret_access_key} onChange={(e) => setAwsKeys({ ...awsKeys, aws_secret_access_key: e.target.value })} />
          </div>
        </>
      );
    }
    if (selectedProvider === 'azure') {
      return (
        <>
          {/* Campos para Azure */}
          <div className="form-group"><label>Azure Client ID</label><input type="text" value={azureKeys.azure_client_id} onChange={e => setAzureKeys({...azureKeys, azure_client_id: e.target.value})} /></div>
          <div className="form-group"><label>Azure Client Secret</label><input type="password" value={azureKeys.azure_client_secret} onChange={e => setAzureKeys({...azureKeys, azure_client_secret: e.target.value})} /></div>
          <div className="form-group"><label>Azure Tenant ID</label><input type="text" value={azureKeys.azure_tenant_id} onChange={e => setAzureKeys({...azureKeys, azure_tenant_id: e.target.value})} /></div>
          <div className="form-group"><label>Azure Subscription ID</label><input type="text" value={azureKeys.azure_subscription_id} onChange={e => setAzureKeys({...azureKeys, azure_subscription_id: e.target.value})} /></div>
        </>
      );
    }
    return null;
  };

  return (
    <div className="credentials-page">
      <h2>Gerenciamento de Credenciais de Nuvem</h2>

      <div className="credentials-container">
        <div className="credentials-form-section">
          <h3>Adicionar / Atualizar Credenciais</h3>
          <form onSubmit={handleSave}>
            <div className="form-group">
              <label>Provedor de Nuvem</label>
              <select value={selectedProvider} onChange={(e) => setSelectedProvider(e.target.value)}>
                <option value="aws">AWS</option>
                <option value="azure">Azure</option>
                {/* Adicionar outros provedores aqui */}
              </select>
            </div>
            {renderForm()}
            <button type="submit">Salvar Credenciais</button>
          </form>
        </div>

        <div className="configured-providers-section">
          <h3>Provedores Configurados</h3>
          <ul>
            {configuredProviders.map(p => (
              <li key={p.provider}>
                <span>{p.provider.toUpperCase()}</span>
                <button onClick={() => handleDelete(p.provider)} className="delete-btn">Deletar</button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};

export default CredentialsPage;

// Adicionar alguns estilos para a página
const styles = `
.credentials-page { padding: 2rem; }
.credentials-container { display: flex; gap: 2rem; }
.credentials-form-section, .configured-providers-section { flex: 1; padding: 1.5rem; background: #f9f9f9; border-radius: 8px; }
.form-group { margin-bottom: 1rem; }
.form-group label { display: block; margin-bottom: 0.5rem; }
.form-group input, .form-group select { width: 100%; padding: 0.5rem; border-radius: 4px; border: 1px solid #ccc; }
button { padding: 0.75rem 1.5rem; border: none; background-color: #007bff; color: white; border-radius: 4px; cursor: pointer; }
button:hover { background-color: #0056b3; }
.delete-btn { background-color: #dc3545; font-size: 0.8rem; padding: 0.4rem 0.8rem; }
.delete-btn:hover { background-color: #c82333; }
ul { list-style: none; padding: 0; }
li { display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; border-bottom: 1px solid #eee; }
`;
const styleSheet = document.createElement("style");
styleSheet.innerText = styles;
document.head.appendChild(styleSheet);
