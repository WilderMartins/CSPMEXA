import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { Title, Box, Skeleton } from '@mantine/core';
import ProviderAnalysisSection from '../../components/Dashboard/ProviderAnalysisSection';
import AlertsTable, { Alert as AlertType } from '../../components/Dashboard/AlertsTable';
import ErrorMessage from '../../components/Common/ErrorMessage';

const GcpDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const auth = useAuth();

  const [alerts, setAlerts] = useState<AlertType[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisType, setAnalysisType] = useState<string | null>(null);

  // Estados para os inputs do GCP
  const [gcpProjectId, setGcpProjectId] = useState<string>('');
  const [gcpLocation, setGcpLocation] = useState<string>('');
  const [sccParentResource, setSccParentResource] = useState<string>('');
  const [sccFilter, setSccFilter] = useState<string>('');
  const [caiScope, setCaiScope] = useState<string>('');
  const [caiAssetTypes, setCaiAssetTypes] = useState<string>('');

  const apiClient = useMemo(() => {
    return axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
      headers: { 'Authorization': `Bearer ${auth.token}` }
    });
  }, [auth.token]);

  const handleAnalysis = async (provider: string, servicePath: string, currentAnalysisType: string, idParams?: Record<string, string | undefined>) => {
    setIsLoading(true);
    setError(null);
    setAlerts([]);
    setAnalysisType(currentAnalysisType);

    const queryParams = new URLSearchParams();
    if (idParams) {
        Object.entries(idParams).forEach(([key, value]) => {
            if (value) queryParams.append(key, value);
        });
    }
    const fullUrl = `/analyze/gcp/${servicePath}?${queryParams.toString()}`;

    try {
      // Validação básica
      if (servicePath !== 'scc/findings' && (!gcpProjectId || gcpProjectId.trim() === '')) {
          throw new Error(t('dashboardPage.gcpProjectIdRequired'));
      }

      const response = await apiClient.post<AlertType[]>(fullUrl, {});
      setAlerts(response.data || []);
      if (response.data.length === 0) {
        setError(t('dashboardPage.noNewAlertsForAnalysis', { type: currentAnalysisType }));
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message;
      setError(t('dashboardPage.errorDuringAnalysis', { type: currentAnalysisType, provider: 'GCP', error: errorMessage }));
    } finally {
      setIsLoading(false);
    }
  };

  const providerConfig = {
    providerNameKey: 'dashboardPage.gcpAnalysisTitle',
    analysisSections: [
        {
            title: 'Análises de Configuração',
            inputFields: [
                { id: 'gcpProjectId', name: 'projectId', labelKey: 'dashboardPage.gcpProjectIdLabel', placeholderKey: 'dashboardPage.gcpProjectIdPlaceholder', value: gcpProjectId, setter: setGcpProjectId },
                { id: 'gcpLocation', name: 'location', labelKey: 'dashboardPage.gcpLocationLabel', placeholderKey: 'dashboardPage.gcpLocationPlaceholder', value: gcpLocation, setter: setGcpLocation, isOptional: true },
            ],
            analysisButtons: [
                { id: 'gcpStorage', labelKey: 'dashboardPage.analyzeGCPStorageButton', servicePath: 'storage/buckets', analysisType: 'GCP Storage Buckets', idParams: { project_id: gcpProjectId } },
                { id: 'gcpComputeInstances', labelKey: 'dashboardPage.analyzeGCPInstancesButton', servicePath: 'compute/instances', analysisType: 'GCP Compute Instances', idParams: { project_id: gcpProjectId } },
                { id: 'gcpFirewalls', labelKey: 'dashboardPage.analyzeGCPFirewallsButton', servicePath: 'compute/firewalls', analysisType: 'GCP Compute Firewalls', idParams: { project_id: gcpProjectId } },
                { id: 'gcpIam', labelKey: 'dashboardPage.analyzeGCPIAMButton', servicePath: 'iam/project-policies', analysisType: 'GCP Project IAM', idParams: { project_id: gcpProjectId } },
                { id: 'gcpGke', labelKey: 'dashboardPage.analyzeGKEClustersButton', servicePath: 'gke/clusters', analysisType: 'GCP GKE Clusters', idParams: { project_id: gcpProjectId, location: gcpLocation } },
            ]
        },
        {
            title: 'Análises de Segurança (SCC & CAI)',
            inputFields: [
                 { id: 'sccParentResource', name: 'parent_resource', labelKey: 'dashboardPage.sccParentResourceLabel', placeholderKey: 'dashboardPage.sccParentResourcePlaceholder', value: sccParentResource, setter: setSccParentResource },
                 { id: 'sccFilter', name: 'scc_filter', labelKey: 'dashboardPage.sccFilterLabel', placeholderKey: 'dashboardPage.sccFilterPlaceholder', value: sccFilter, setter: setSccFilter, isOptional: true },
                 { id: 'caiScope', name: 'scope', labelKey: 'dashboardPage.caiScopeLabel', placeholderKey: 'dashboardPage.caiScopePlaceholder', value: caiScope, setter: setCaiScope },
                 { id: 'caiAssetTypes', name: 'asset_types', labelKey: 'dashboardPage.caiAssetTypesLabel', placeholderKey: 'dashboardPage.caiAssetTypesPlaceholder', value: caiAssetTypes, setter: setCaiAssetTypes, isOptional: true },
            ],
            analysisButtons: [
                { id: 'sccFindings', labelKey: 'dashboardPage.analyzeSCCFindingsButton', servicePath: 'scc/findings', analysisType: 'GCP SCC Findings', idParams: { parent_resource: sccParentResource, scc_filter: sccFilter } },
                { id: 'caiAssets', labelKey: 'dashboardPage.analyzeCAIAssetsButton', servicePath: 'cai/assets', analysisType: 'GCP CAI Assets', idParams: { scope: caiScope, asset_types: caiAssetTypes } },
            ]
        }
    ]
  };

  return (
    <div>
      <Title order={2} mb="xl">{t(providerConfig.providerNameKey, 'GCP Analysis')}</Title>

      {providerConfig.analysisSections.map(section => (
        <Box key={section.title} mb="xl">
            <Title order={4} mb="md">{section.title}</Title>
            <ProviderAnalysisSection
                providerId="gcp"
                inputFields={section.inputFields}
                analysisButtons={section.analysisButtons}
                onAnalyze={(provider, servicePath, currentAnalysisType, idParams) => handleAnalysis(provider, servicePath, currentAnalysisType, idParams)}
                isLoading={isLoading}
                currentAnalysisType={analysisType}
            />
        </Box>
      ))}

      <ErrorMessage message={error} onClose={() => setError(null)} />

      {isLoading && !error && (
         <Box mt="xl">
            <Skeleton height={25} mt="md" />
            <Skeleton height={25} mt="xs" />
            <Skeleton height={25} mt="xs" />
          </Box>
      )}

      {!isLoading && !error && alerts.length > 0 && (
        <AlertsTable
          alerts={alerts}
          title={t('dashboardPage.alertsFoundFor', { type: analysisType })}
          onUpdateStatus={async () => {}}
          canUpdateStatus={false}
        />
      )}
    </div>
  );
};

export default GcpDashboardPage;
