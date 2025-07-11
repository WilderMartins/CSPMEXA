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
    // const response = await apiClient.get<SecurityScoreTrendPoint[]>('/reports/security-score-trend', { params: filters });
    // return response.data;

    // Mock data enquanto o endpoint não existe
    console.warn("fetchSecurityScoreTrend: Usando dados mockados. Endpoint real necessário: GET /api/v1/reports/security-score-trend");
    await new Promise(resolve => setTimeout(resolve, 500)); // Simula delay da API
    return [
      { date: "2023-05-01", overallScore: 70, criticalAlerts: 8, highAlerts: 12, awsScore: 75 },
      { date: "2023-05-08", overallScore: 72, criticalAlerts: 6, highAlerts: 10, awsScore: 77 },
      { date: "2023-05-15", overallScore: 75, criticalAlerts: 4, highAlerts: 8, awsScore: 80 },
      { date: "2023-05-22", overallScore: 73, criticalAlerts: 5, highAlerts: 9, awsScore: 78 },
    ];
  } catch (error) {
    console.error('Error fetching security score trend:', error);
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
    // const response = await apiClient.get<AlertsSummaryDataPoint[]>('/reports/alerts-summary', { params: filters });
    // return response.data;

    console.warn("fetchAlertsSummary: Usando dados mockados. Endpoint real necessário: GET /api/v1/reports/alerts-summary");
    await new Promise(resolve => setTimeout(resolve, 500));
    // A lógica de mock pode ser ajustada para retornar dados diferentes baseados nos filtros, se necessário para testes.
    if (filters.group_by === 'severity' || !filters.group_by) {
      return [
        { severity: "Critical", count: 15, percentage: 10 },
        { severity: "High", count: 30, percentage: 20 },
        { severity: "Medium", count: 75, percentage: 50 },
        { severity: "Low", count: 30, percentage: 20 },
      ];
    } else if (params.group_by === 'provider') {
       return [
        { provider: "AWS", count: 100, openAlerts: 50 },
        { provider: "GCP", count: 40, openAlerts: 15 },
        { provider: "Azure", count: 10, openAlerts: 5 },
      ];
    }
    return [];
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
    // const response = await apiClient.get<ComplianceOverview>('/reports/compliance-overview', { params: filters });
    // return response.data;

    console.warn("fetchComplianceOverview: Usando dados mockados. Endpoint real necessário: GET /api/v1/reports/compliance-overview");
    await new Promise(resolve => setTimeout(resolve, 500));
    return {
      framework: "CIS AWS Foundations Benchmark v1.4.0 (Mocked)",
      overallCompliance: 75.5,
      controls: [
        { controlId: "1.1", description: "Avoid the use of the root account (Mocked)", status: "Compliant", failingChecks: 0, totalChecks: 5 },
        { controlId: "1.2", description: "Ensure MFA is enabled for all IAM users (Mocked)", status: "Non-Compliant", failingChecks: 2, totalChecks: 10 },
        { controlId: "1.3", description: "Ensure credentials unused for 90 days or greater are disabled (Mocked)", status: "Compliant", failingChecks: 1, totalChecks: 20 },
      ]
    };
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
    // const response = await apiClient.get<TopRisk[]>('/reports/top-risks', { params: filters });
    // return response.data;

    console.warn("fetchTopRisks: Usando dados mockados. Endpoint real necessário: GET /api/v1/reports/top-risks");
    await new Promise(resolve => setTimeout(resolve, 500));
    return [
      { policyTitle: "S3 Bucket Publicly Accessible (Mocked)", severity: "Critical", instanceCount: 5, provider: "AWS" },
      { policyTitle: "Unrestricted SSH Access (Mocked)", severity: "High", instanceCount: 8, provider: "AWS" },
      { policyTitle: "VM using Default Service Account (Mocked)", severity: "Medium", instanceCount: 12, provider: "GCP" },
    ];
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
  console.warn("fetchCriticalAssets: Usando dados mockados. Endpoint real necessário: GET /api/v1/insights/critical-assets");
  await new Promise(resolve => setTimeout(resolve, 600));
  return [
    { id: 'asset-001', name: 'Prod DB Server', type: 'RDS Instance', riskScore: 95, relatedAlertsCount: 5, provider: filters?.provider || 'AWS' },
    { id: 'asset-002', name: 'Main K8s Cluster', type: 'EKS Cluster', riskScore: 88, relatedAlertsCount: 3, provider: filters?.provider || 'AWS' },
    { id: 'asset-003', name: 'Billing Storage', type: 'S3 Bucket', riskScore: 92, relatedAlertsCount: 7, provider: filters?.provider || 'AWS' },
  ];
};

/**
 * Busca dados de caminhos de ataque potenciais (mockado).
 * @returns Uma Promise com uma lista de caminhos de ataque.
 */
export const fetchAttackPaths = async (filters?: { provider?: string }): Promise<AttackPath[]> => {
  console.warn("fetchAttackPaths: Usando dados mockados. Endpoint real necessário: GET /api/v1/insights/attack-paths");
  await new Promise(resolve => setTimeout(resolve, 700));
  return [
    {
      id: 'ap-001',
      description: `Public EC2 Instance ${filters?.provider || 'AWS'}-Instance-123 to Sensitive Data S3 Bucket`,
      path: [
        { resourceId: `${filters?.provider || 'AWS'}-Instance-123`, resourceType: 'EC2 Instance', vulnerability: 'Publicly Exposed, Unrestricted SG' },
        { resourceId: 'internal-network-hop', resourceType: 'Network Path', vulnerability: 'Assumed Internal Access' },
        { resourceId: `${filters?.provider || 'AWS'}-S3-Sensitive-Data`, resourceType: 'S3 Bucket', vulnerability: 'Readable by Instance Role' }
      ],
      severity: 'High'
    },
  ];
};

/**
 * Busca recomendações proativas (mockado).
 * @returns Uma Promise com uma lista de recomendações proativas.
 */
export const fetchProactiveRecommendations = async (filters?: { category?: string }): Promise<ProactiveRecommendation[]> => {
  console.warn("fetchProactiveRecommendations: Usando dados mockados. Endpoint real necessário: GET /api/v1/insights/proactive-recommendations");
  await new Promise(resolve => setTimeout(resolve, 400));
  return [
    { id: 'rec-001', title: 'Enable MFA for all IAM Users', description: 'Multiple IAM users without MFA detected. MFA adds a critical layer of security.', category: 'IAM', severity: 'High' },
    { id: 'rec-002', title: 'Restrict Public S3 Bucket Access', description: 'Review and restrict policies战争 S3 buckets that allow public read/write access.', category: 'Data Security', severity: 'Critical' },
    { id: 'rec-003', title: 'Implement Least Privilege for Service Accounts (GCP)', description: 'Several default service accounts have broad permissions. Assign granular roles instead.', category: 'IAM', severity: 'Medium' },
  ];
};
