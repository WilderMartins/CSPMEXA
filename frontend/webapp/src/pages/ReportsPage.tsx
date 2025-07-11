import React, { useEffect, useState, useMemo } from 'react'; // Adicionado useEffect, useState
import { useTranslation } from 'react-i18next';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar
} from 'recharts'; // Importar componentes reais do Recharts uma vez

// Componentes UI (Paper, Title) - Definidos uma vez
// Estes poderiam ser movidos para um diretório de componentes compartilhados se usados em mais lugares.
const Paper: React.FC<{ children: React.ReactNode, padding?: string | number, shadow?: string, style?: React.CSSProperties }> = ({ children, style, padding = 'md', shadow = 'sm', ...props }) => (
  <div
    style={{
      padding: typeof padding === 'number' ? `${padding}px` : padding,
      boxShadow: shadow === 'sm' ? `0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.1)` : 'none',
      border: '1px solid #e0e0e0',
      borderRadius: '5px',
      marginBottom: '20px',
      ...style
    }}
    {...props}
  >
    {children}
  </div>
);

const Title: React.FC<{ order?: 1 | 2 | 3 | 4 | 5 | 6, children: React.ReactNode, style?: React.CSSProperties }> = ({ order = 3, children, style }) => {
  const Tag = `h${order}` as keyof JSX.IntrinsicElements;
  return <Tag style={{ marginTop: 0, marginBottom: '1rem', fontWeight: 600, ...style }}>{children}</Tag>;
};

// Não há mais componentes simulados de Recharts aqui

/**
 * `ReportsPage` é a página responsável por exibir diversos relatórios e indicadores
 * de segurança, como tendência da pontuação de segurança, alertas por severidade, etc.
 * Utiliza a biblioteca Recharts para visualização de dados.
 *
 * @component
 */
import {
  fetchSecurityScoreTrend,
  fetchAlertsSummary,
  fetchComplianceOverview,
  fetchTopRisks,
  SecurityScoreTrendPoint,
  AlertsSummaryDataPoint,
  ComplianceOverview as ComplianceOverviewType, // Renomeado para evitar conflito com nome de componente
  TopRisk
} from '../services/reportsService'; // Importar os serviços

// Dados de exemplo para os gráficos - REMOVIDOS, serão buscados
// const sampleTrendData = [...]
// const sampleAlertsBySeverityData = [...]

const ReportsPage: React.FC = () => {
  const { t } = useTranslation();

  // Estados para os dados dos relatórios
  const [securityScoreTrend, setSecurityScoreTrend] = useState<SecurityScoreTrendPoint[]>([]);
  const [alertsBySeverity, setAlertsBySeverity] = useState<AlertsSummaryDataPoint[]>([]);
  const [complianceOverview, setComplianceOverview] = useState<ComplianceOverviewType | null>(null);
  const [topRisks, setTopRisks] = useState<TopRisk[]>([]);

  // Estados para os filtros
  const [selectedPeriod, setSelectedPeriod] = useState<'weekly' | 'monthly' | 'daily' | 'custom'>('weekly');
  const [selectedProvider, setSelectedProvider] = useState<string>(''); // '' para todos
  // TODO: Adicionar estados para range_start, range_end se selectedPeriod for 'custom'

  // Estados de Carregamento
  const [isLoadingTrend, setIsLoadingTrend] = useState(true);
  const [isLoadingSeverity, setIsLoadingSeverity] = useState(true);
  const [isLoadingCompliance, setIsLoadingCompliance] = useState(true);
  const [isLoadingTopRisks, setIsLoadingTopRisks] = useState(true);

  const [errorTrend, setErrorTrend] = useState<string | null>(null);
  const [errorSeverity, setErrorSeverity] = useState<string | null>(null);
  const [errorCompliance, setErrorCompliance] = useState<string | null>(null);
  const [errorTopRisks, setErrorTopRisks] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      // Filtros a serem passados para as funções de serviço
      const filters = {
        period: selectedPeriod,
        provider: selectedProvider || undefined, // Envia undefined se '' para não enviar o parâmetro
        // range_start e range_end seriam adicionados aqui se selectedPeriod for 'custom'
      };

      try {
        setIsLoadingTrend(true);
        const trendData = await fetchSecurityScoreTrend(filters);
        setSecurityScoreTrend(trendData);
        setErrorTrend(null);
      } catch (err) {
        setErrorTrend(t('reportsPage.errorFetchingTrend'));
      } finally {
        setIsLoadingTrend(false);
      }

      try {
        setIsLoadingSeverity(true);
        // Para alertsSummary, podemos querer manter group_by fixo ou torná-lo outro filtro
        const severityData = await fetchAlertsSummary({ group_by: 'severity', ...filters });
        setAlertsBySeverity(severityData);
        setErrorSeverity(null);
      } catch (err) {
        setErrorSeverity(t('reportsPage.errorFetchingSeverity'));
      } finally {
        setIsLoadingSeverity(false);
      }

      try {
        setIsLoadingCompliance(true);
        const complianceData = await fetchComplianceOverview({ provider: filters.provider }); // Apenas provider por enquanto
        setComplianceOverview(complianceData);
        setErrorCompliance(null);
      } catch (err) {
        setErrorCompliance(t('reportsPage.errorFetchingCompliance'));
      } finally {
        setIsLoadingCompliance(false);
      }

      try {
        setIsLoadingTopRisks(true);
        const risksData = await fetchTopRisks({ provider: filters.provider, limit: 10 }); // Provider e um limite exemplo
        setTopRisks(risksData);
        setErrorTopRisks(null);
      } catch (err) {
        setErrorTopRisks(t('reportsPage.errorFetchingTopRisks'));
      } finally {
        setIsLoadingTopRisks(false);
      }
    };
    loadData();
  }, [t, selectedPeriod, selectedProvider]); // Re-executar quando os filtros mudarem

  // Opções para os seletores de filtro
  const periodOptions = [
    { value: 'daily', label: t('reportsPage.filterOptions.daily', 'Daily') },
    { value: 'weekly', label: t('reportsPage.filterOptions.weekly', 'Weekly') },
    { value: 'monthly', label: t('reportsPage.filterOptions.monthly', 'Monthly') },
    // { value: 'custom', label: t('reportsPage.filterOptions.custom', 'Custom Range') }, // Para quando DatePicker for implementado
  ];

  const providerOptions = [
    { value: '', label: t('reportsPage.filterOptions.allProviders', 'All Providers') },
    { value: 'AWS', label: 'AWS' },
    { value: 'GCP', label: 'GCP' },
    { value: 'Azure', label: 'Azure' },
    { value: 'Huawei', label: 'Huawei Cloud' },
    { value: 'GoogleWorkspace', label: 'Google Workspace' },
  ];

  // Componente Select simulado (deveria ser importado de um local comum ou biblioteca UI)
  const Select: React.FC<React.SelectHTMLAttributes<HTMLSelectElement> & { label?: string, data: Array<{value: string, label: string}>, containerStyle?: React.CSSProperties }> =
    ({ label, data, containerStyle, ...props }) => (
    <div style={{ display: 'inline-block', marginRight: '20px', marginBottom: '20px', ...containerStyle }}>
      {label && <label htmlFor={props.id} style={{ marginRight: '8px', fontSize: '0.9em', fontWeight: 500 }}>{label}:</label>}
      <select
        id={props.id}
        style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #ccc', minWidth: '150px' }}
        {...props}
      >
        {data.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
      </select>
    </div>
  );


  return (
    <div className="reports-page" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <Title order={1} style={{ marginBottom: '20px', textAlign: 'center' }}>{t('reportsPage.title')}</Title>

      {/* Seção de Filtros */}
      <Paper padding="lg" shadow="xs" style={{marginBottom: '30px', background: '#f9f9f9'}}>
        <Title order={3} style={{marginBottom: '20px', borderBottom: '1px solid #eee', paddingBottom: '10px'}}>{t('reportsPage.filtersTitle', 'Filters')}</Title>
        <div style={{display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '20px'}}>
          <Select
            id="period-filter"
            label={t('reportsPage.filterLabelPeriod', 'Period')}
            data={periodOptions}
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value as any)}
          />
          <Select
            id="provider-filter"
            label={t('reportsPage.filterLabelProvider', 'Provider')}
            data={providerOptions}
            value={selectedProvider}
            onChange={(e) => setSelectedProvider(e.target.value)}
          />
          {/* TODO: Adicionar DatePickers aqui se selectedPeriod for 'custom' */}
        </div>
      </Paper>

      {/* Layout dos Gráficos: Considerar um layout de grade (ex: 2 colunas) para melhor visualização */}
      {/* Exemplo: <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}> */}
      <Paper>
        <Title order={2}>{t('reportsPage.securityScoreTrendTitle')}</Title>
        {isLoadingTrend && <p>{t('reportsPage.loadingData')}</p>}
        {errorTrend && <p style={{ color: 'red' }}>{errorTrend}</p>}
        {!isLoadingTrend && !errorTrend && securityScoreTrend.length === 0 && <p>{t('reportsPage.noDataAvailable')}</p>}
        {!isLoadingTrend && !errorTrend && securityScoreTrend.length > 0 && (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={securityScoreTrend} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis yAxisId="left" label={{ value: t('reportsPage.securityScoreAxisLabel'), angle: -90, position: 'insideLeft', style: {textAnchor: 'middle'} }} />
              <YAxis yAxisId="right" orientation="right" label={{ value: t('reportsPage.alertsAxisLabel'), angle: 90, position: 'insideRight', style: {textAnchor: 'middle'} }} />
              <Tooltip />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="overallScore" name={t('reportsPage.overallScoreLegend')} stroke="#8884d8" activeDot={{ r: 6 }} dot={{ r: 3 }}/>
              <Line yAxisId="right" type="monotone" dataKey="criticalAlerts" name={t('reportsPage.criticalAlertsLegend')} stroke="#ff7300" dot={{ r: 3 }} />
              <Line yAxisId="right" type="monotone" dataKey="highAlerts" name={t('reportsPage.highAlertsLegend')} stroke="#ffc658" dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        )}
        {/* Mostrar aviso de dados mockados se não houver erro e os dados forem os mockados (identificável pela presença de awsScore por ex.) */}
        {!isLoadingTrend && !errorTrend && securityScoreTrend.some(d => d.awsScore !== undefined) && <p style={{marginTop: '10px', fontSize: '0.8em', color: '#777'}}>{t('reportsPage.dataDisclaimer')}</p>}
      </Paper>

      <Paper>
        <Title order={2}>{t('reportsPage.alertsBySeverityTitle')}</Title>
        {isLoadingSeverity && <p>{t('reportsPage.loadingData')}</p>}
        {errorSeverity && <p style={{ color: 'red' }}>{errorSeverity}</p>}
        {!isLoadingSeverity && !errorSeverity && alertsBySeverity.length === 0 && <p>{t('reportsPage.noDataAvailable')}</p>}
        {!isLoadingSeverity && !errorSeverity && alertsBySeverity.length > 0 && (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={alertsBySeverity} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              {/* A chave do XAxis deve corresponder ao que é retornado pelo backend (severity, provider, etc.) */}
              <XAxis dataKey={alertsBySeverity[0]?.severity ? "severity" : (alertsBySeverity[0]?.provider ? "provider" : "name")} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" name={t('reportsPage.alertCountLegend')} fill="#82ca9d" />
            </BarChart>
          </ResponsiveContainer>
        )}
         {!isLoadingSeverity && !errorSeverity && alertsBySeverity.length > 0 && <p style={{marginTop: '10px', fontSize: '0.8em', color: '#777'}}>{t('reportsPage.dataDisclaimer')}</p>}
      </Paper>

      <Paper>
        <Title order={2}>{t('reportsPage.complianceOverviewTitle')}</Title>
        <p>{t('reportsPage.dataDisclaimer')}</p>
        {/* TODO: Implementar visualização de compliance. Ex: Tabela ou gráfico de pizza */}
        <p>{t('reportsPage.compliancePlaceholder')}</p>
        {/* Exemplo:
          <ResponsiveContainer height={200}>
             <PieChart> <Pie data={complianceData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} fill="#8884d8" label /> <Tooltip/> </PieChart>
          </ResponsiveContainer>
        */}
      </Paper>

      <Paper>
        <Title order={2}>{t('reportsPage.topRisksTitle')}</Title>
        <p>{t('reportsPage.dataDisclaimer')}</p>
        {/* TODO: Implementar visualização dos principais riscos. Ex: Lista ou tabela */}
        <p>{t('reportsPage.topRisksPlaceholder')}</p>
        {/* Exemplo:
          <ul>
            {topRisks.map(risk => <li key={risk.id}>{risk.description} - Severity: {risk.severity}</li>)}
          </ul>
        */}
      </Paper>

    </div>
  );
};

export default ReportsPage;
