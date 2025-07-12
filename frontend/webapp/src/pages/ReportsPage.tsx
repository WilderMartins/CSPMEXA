import React, { useEffect, useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar
} from 'recharts';
import { Paper, Title, Select } from '@mantine/core'; // Usar Select da Mantine diretamente

// Remover a definição do Select simulado localmente

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

  // A definição do Select simulado foi removida. Usaremos o Select importado da Mantine.

  return (
    <div className="reports-page" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <Title order={1} ta="center" mb="xl">{t('reportsPage.title')}</Title> {/* Usar props Mantine */}

      {/* Seção de Filtros */}
      <Paper p="lg" shadow="xs" radius="md" withBorder mb="xl" style={{background: 'var(--mantine-color-gray-0)'}}> {/* Usar props e theme Mantine */}
        <Title order={3} mb="lg" style={{borderBottom: `1px solid var(--mantine-color-gray-3)`, paddingBottom: 'var(--mantine-spacing-sm)'}}>{t('reportsPage.filtersTitle', 'Filters')}</Title>
        <div style={{display: 'flex', flexWrap: 'wrap', alignItems: 'flex-end', gap: '20px'}}> {/* alignItems: flex-end para alinhar labels e inputs */}
          <Select // Este agora é o Mantine Select
            label={t('reportsPage.filterLabelPeriod', 'Period')}
            placeholder={t('reportsPage.filterOptions.selectPeriod', 'Select period')}
            data={periodOptions}
            value={selectedPeriod}
            onChange={(value) => setSelectedPeriod(value as any)} // value pode ser null se clearable
            clearable
            allowDeselect={false}
            style={{minWidth: '200px'}}
            comboboxProps={{ shadow: 'md', transitionProps: { transition: 'pop', duration: 200 } }}
          />
          <Select // Este agora é o Mantine Select
            label={t('reportsPage.filterLabelProvider', 'Provider')}
            placeholder={t('reportsPage.filterOptions.selectProvider', 'Select provider')}
            data={providerOptions}
            value={selectedProvider}
            onChange={(value) => setSelectedProvider(value || '')} // value pode ser null, converter para ''
            clearable
            style={{minWidth: '200px'}}
            comboboxProps={{ shadow: 'md', transitionProps: { transition: 'pop', duration: 200 } }}
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
