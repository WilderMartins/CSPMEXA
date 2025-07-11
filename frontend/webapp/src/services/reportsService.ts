import axios from 'axios';

/**
 * apiClient é uma instância do axios pré-configurada.
 * Idealmente, ela seria importada de um local central onde já está
 * configurada com baseURL e interceptors (incluindo o token de autenticação).
 * Para este exemplo, vamos simular a sua existência ou criar uma nova.
 * Em um projeto real, você provavelmente usaria a mesma instância do AuthContext ou uma similar.
 */
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  // O token de autenticação seria adicionado por um interceptor
  // ou buscado do AuthContext e adicionado aos headers aqui, se necessário.
  // Exemplo: headers: { 'Authorization': `Bearer ${getTokenFromAuthContext()}` }
});

// Interceptor para adicionar o token do localStorage (semelhante ao DashboardPage)
// Em uma aplicação maior, isso estaria em um setup central do axios.
apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, error => {
  return Promise.reject(error);
});


// --- Tipos de Dados Esperados dos Endpoints (Exemplos) ---

export interface SecurityScoreTrendPoint {
  date: string; // Formato YYYY-MM-DD
  overallScore: number;
  awsScore?: number;
  gcpScore?: number;
  azureScore?: number;
  criticalAlerts: number;
  highAlerts: number;
}

export interface AlertsSummaryDataPoint {
  // Para group_by=severity
  severity?: 'Critical' | 'High' | 'Medium' | 'Low' | 'Informational';
  // Para group_by=status
  status?: string; // Ex: 'Open', 'Closed', 'Acknowledged'
  // Para group_by=provider
  provider?: 'AWS' | 'GCP' | 'Azure' | 'Huawei' | 'GoogleWorkspace';
  // Para group_by=resource_type
  resource_type?: string;

  count: number;
  percentage?: number; // Opcional, pode ser calculado no frontend
  openAlerts?: number; // Específico para group_by=provider, por exemplo
}

export interface ComplianceControl {
  controlId: string;
  description: string;
  status: 'Compliant' | 'Non-Compliant' | 'Not-Assessed';
  failingChecks: number;
  totalChecks: number;
}
export interface ComplianceOverview {
  framework: string;
  overallCompliance: number; // percentual
  controls: ComplianceControl[];
}

export interface TopRisk {
  policyTitle: string;
  severity: string;
  instanceCount: number;
  provider: string;
}

// --- Funções de Serviço ---

/**
 * Busca dados de tendência da pontuação de segurança.
 * @param params Parâmetros de filtro opcionais.
 * @returns Uma Promise com a lista de pontos de dados da tendência.
 */
export const fetchSecurityScoreTrend = async (filters?: { // Renomeado para filters para clareza
  period?: 'daily' | 'weekly' | 'monthly' | 'custom'; // Adicionado 'custom' para range
  range_start?: string; // YYYY-MM-DD
  range_end?: string;   // YYYY-MM-DD
  provider?: string; // ex: 'AWS', 'GCP', '' para todos
}): Promise<SecurityScoreTrendPoint[]> => {
  try {
    const response = await apiClient.get<SecurityScoreTrendPoint[]>('/reports/security-score-trend', { params: filters });
    return response.data;
  } catch (error) {
    console.error('Error fetching security score trend:', error);
    // Lançar o erro permite que o componente que chama trate a UI de erro
    // Pode-se também retornar um array vazio ou um objeto de erro customizado se preferir
    throw error;
  }
};

/**
 * Busca dados de resumo de alertas.
 * @param params Parâmetros de filtro e agrupamento.
 * @returns Uma Promise com a lista de pontos de dados do resumo.
 */
export const fetchAlertsSummary = async (filters: { // Renomeado para filters
  group_by?: 'severity' | 'status' | 'provider' | 'resource_type';
  provider?: string; // ex: 'AWS', 'GCP', '' para todos
  period?: 'daily' | 'weekly' | 'monthly' | 'custom'; // Adicionado 'custom' para range
  range_start?: string; // YYYY-MM-DD
  range_end?: string;   // YYYY-MM-DD
}): Promise<AlertsSummaryDataPoint[]> => {
  try {
    const response = await apiClient.get<AlertsSummaryDataPoint[]>('/reports/alerts-summary', { params: filters });
    return response.data;
  } catch (error) {
    console.error('Error fetching alerts summary:', error);
    throw error;
  }
};

/**
 * Busca dados de visão geral de compliance.
 * @param params Parâmetros de filtro opcionais (ex: framework).
 * @returns Uma Promise com os dados de compliance.
 */
export const fetchComplianceOverview = async (filters?: { // Renomeado para filters
  framework?: string; // ex: 'CIS', 'NIST', '' para todos
  provider?: string; // ex: 'AWS', 'GCP', '' para todos
}): Promise<ComplianceOverview> => {
  try {
    const response = await apiClient.get<ComplianceOverview>('/reports/compliance-overview', { params: filters });
    return response.data;
  } catch (error) {
    console.error('Error fetching compliance overview:', error);
    throw error;
  }
};

/**
 * Busca dados dos principais riscos.
 * @param params Parâmetros de filtro opcionais.
 * @returns Uma Promise com a lista dos principais riscos.
 */
export const fetchTopRisks = async (filters?: { // Renomeado para filters
  limit?: number;
  provider?: string; // ex: 'AWS', 'GCP', '' para todos
  severity?: 'Critical' | 'High' | ''; // Filtrar por severidade mínima
}): Promise<TopRisk[]> => {
  try {
    const response = await apiClient.get<TopRisk[]>('/reports/top-risks', { params: filters });
    return response.data;
  } catch (error) {
    console.error('Error fetching top risks:', error);
    throw error;
  }
};

// Adicionar aqui funções para buscar dados para o Dashboard de Insights quando os endpoints forem definidos.

/**
 * Representa um ativo crítico identificado pelo sistema de insights.
 */
export interface CriticalAsset {
  /** Identificador único do ativo. */
  id: string;
  /** Nome do ativo. */
  name: string;
  /** Tipo do ativo (ex: RDS Instance, EKS Cluster). */
  type: string;
  /** Pontuação de risco calculada para o ativo. */
  riskScore: number;
  /** Número de alertas de segurança relacionados a este ativo. */
  relatedAlertsCount: number;
  /** Provedor de nuvem onde o ativo está localizado. */
  provider: string;
}

/**
 * Representa um segmento individual em um caminho de ataque potencial.
 */
export interface AttackPathSegment {
  /** Identificador do recurso neste segmento do caminho. */
  resourceId: string;
  /** Tipo do recurso. */
  resourceType: string;
  /** Descrição da vulnerabilidade ou configuração incorreta explorada neste segmento. */
  vulnerability: string;
}

/**
 * Representa um caminho de ataque potencial identificado.
 */
export interface AttackPath {
  /** Identificador único do caminho de ataque. */
  id: string;
  /** Descrição resumida do caminho de ataque. */
  description: string;
  /** Lista ordenada de segmentos que compõem o caminho de ataque. */
  path: AttackPathSegment[];
  /** Severidade geral do caminho de ataque. */
  severity: 'High' | 'Medium' | 'Low';
}

/**
 * Representa uma recomendação proativa gerada pelo sistema de insights.
 */
export interface ProactiveRecommendation {
  /** Identificador único da recomendação. */
  id: string;
  /** Título da recomendação. */
  title: string;
  /** Descrição detalhada da recomendação e sua justificativa. */
  description: string;
  /** Categoria da recomendação (ex: IAM, Network, Data Security). */
  category: string;
  /** Severidade ou importância da recomendação. */
  severity: 'High' | 'Medium' | 'Low';
}


/**
 * Busca dados de ativos críticos em risco (mockado).
 * @returns Uma Promise com uma lista de ativos críticos.
 */
export const fetchCriticalAssets = async (filters?: { provider?: string }): Promise<CriticalAsset[]> => {
  try {
    const response = await apiClient.get<CriticalAsset[]>('/insights/critical-assets', { params: filters });
    return response.data;
  } catch (error) {
    console.error('Error fetching critical assets:', error);
    throw error;
  }
};

/**
 * Busca dados de caminhos de ataque potenciais (mockado).
 * @returns Uma Promise com uma lista de caminhos de ataque.
 */
export const fetchAttackPaths = async (filters?: { provider?: string }): Promise<AttackPath[]> => {
  try {
    const response = await apiClient.get<AttackPath[]>('/insights/attack-paths', { params: filters });
    return response.data;
  } catch (error) {
    console.error('Error fetching attack paths:', error);
    throw error;
  }
};

/**
 * Busca recomendações proativas (mockado).
 * @returns Uma Promise com uma lista de recomendações proativas.
 */
export const fetchProactiveRecommendations = async (filters?: { category?: string }): Promise<ProactiveRecommendation[]> => {
  try {
    const response = await apiClient.get<ProactiveRecommendation[]>('/insights/proactive-recommendations', { params: filters });
    return response.data;
  } catch (error) {
    console.error('Error fetching proactive recommendations:', error);
    throw error;
  }
};
