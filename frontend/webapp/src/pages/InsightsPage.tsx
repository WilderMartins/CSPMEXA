import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  fetchCriticalAssets,
  fetchAttackPaths,
  fetchProactiveRecommendations,
  CriticalAsset,
  AttackPath,
  ProactiveRecommendation,
} from '../../services/reportsService'; // Ajuste o caminho se necessário

import CriticalAssetsDisplay from '../../components/Insights/CriticalAssetsDisplay';
import AttackPathsDisplay from '../../components/Insights/AttackPathsDisplay';
import ProactiveRecommendationsDisplay from '../../components/Insights/ProactiveRecommendationsDisplay';

// Componentes UI simulados (Paper, Title) - mantidos para consistência de estilo da página
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

/**
 * `InsightsPage` é a página dedicada a apresentar insights de segurança mais elaborados,
 * como ativos críticos em risco, potenciais caminhos de ataque e recomendações proativas.
 * Os dados são obtidos através de serviços (atualmente mockados) e exibidos usando
 * componentes de display customizados.
 *
 * @component
 */
const InsightsPage: React.FC = () => {
  const { t } = useTranslation();

  const [criticalAssets, setCriticalAssets] = useState<CriticalAsset[]>([]);
  const [isLoadingCriticalAssets, setIsLoadingCriticalAssets] = useState(true);
  const [errorCriticalAssets, setErrorCriticalAssets] = useState<string | null>(null);

  const [attackPaths, setAttackPaths] = useState<AttackPath[]>([]);
  const [isLoadingAttackPaths, setIsLoadingAttackPaths] = useState(true);
  const [errorAttackPaths, setErrorAttackPaths] = useState<string | null>(null);

  const [recommendations, setRecommendations] = useState<ProactiveRecommendation[]>([]);
  const [isLoadingRecommendations, setIsLoadingRecommendations] = useState(true);
  const [errorRecommendations, setErrorRecommendations] = useState<string | null>(null);

  useEffect(() => {
    const loadInsightsData = async () => {
      // Fetch Critical Assets
      try {
        setIsLoadingCriticalAssets(true);
        const assets = await fetchCriticalAssets();
        setCriticalAssets(assets);
        setErrorCriticalAssets(null);
      } catch (err) {
        setErrorCriticalAssets(t('insightsPage.errorCriticalAssets', 'Failed to load critical assets.'));
      } finally {
        setIsLoadingCriticalAssets(false);
      }

      // Fetch Attack Paths
      try {
        setIsLoadingAttackPaths(true);
        const paths = await fetchAttackPaths();
        setAttackPaths(paths);
        setErrorAttackPaths(null);
      } catch (err) {
        setErrorAttackPaths(t('insightsPage.errorAttackPaths', 'Failed to load attack paths.'));
      } finally {
        setIsLoadingAttackPaths(false);
      }

      // Fetch Proactive Recommendations
      try {
        setIsLoadingRecommendations(true);
        const recs = await fetchProactiveRecommendations();
        setRecommendations(recs);
        setErrorRecommendations(null);
      } catch (err) {
        setErrorRecommendations(t('insightsPage.errorRecommendations', 'Failed to load recommendations.'));
      } finally {
        setIsLoadingRecommendations(false);
      }
    };

    loadInsightsData();
  }, [t]); // Adicionar 't' como dependência para as mensagens de erro

  return (
    <div className="insights-page" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <Title order={1} style={{ marginBottom: '30px', textAlign: 'center' }}>
        {t('insightsPage.title', 'Security Insights')}
      </Title>

      <Paper>
        <Title order={2} style={{borderBottom: '1px solid #eee', paddingBottom: '10px', marginBottom: '20px'}}>
          {t('insightsPage.criticalAssetsTitle', 'Critical Assets at Risk')}
        </Title>
        <CriticalAssetsDisplay
          assets={criticalAssets}
          isLoading={isLoadingCriticalAssets}
          error={errorCriticalAssets}
        />
      </Paper>

      <Paper>
        <Title order={2} style={{borderBottom: '1px solid #eee', paddingBottom: '10px', marginBottom: '20px'}}>
          {t('insightsPage.attackPathsTitle', 'Potential Attack Paths (Simplified)')}
        </Title>
        <AttackPathsDisplay
          paths={attackPaths}
          isLoading={isLoadingAttackPaths}
          error={errorAttackPaths}
        />
      </Paper>

      <Paper>
        <Title order={2} style={{borderBottom: '1px solid #eee', paddingBottom: '10px', marginBottom: '20px'}}>
          {t('insightsPage.proactiveRecommendationsTitle', 'Proactive Recommendations')}
        </Title>
        <ProactiveRecommendationsDisplay
          recommendations={recommendations}
          isLoading={isLoadingRecommendations}
          error={errorRecommendations}
        />
      </Paper>
    </div>
  );
};

export default InsightsPage;
