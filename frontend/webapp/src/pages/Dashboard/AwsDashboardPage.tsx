import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Title, Box, Skeleton } from '@mantine/core';
import ProviderAnalysisSection from '../../components/Dashboard/ProviderAnalysisSection';
import AlertsTable, { Alert as AlertType } from '../../components/Dashboard/AlertsTable';
import ErrorMessage from '../../components/Common/ErrorMessage';
import { apiClient } from '../../services/reportsService'; // Importando o apiClient centralizado

const AwsDashboardPage: React.FC = () => {
  const { t } = useTranslation();

  const [alerts, setAlerts] = useState<AlertType[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisType, setAnalysisType] = useState<string | null>(null);

  const handleRemediation = async (alert: AlertType) => {
    if (alert.policy_id !== 'S3_BUCKET_PUBLIC_ACL') {
      setError(t('dashboardPage.remediationNotSupported', { policy: alert.policy_id }));
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await apiClient.post(`/remediate/aws/s3/public-acl`, {
        credentials: {}, // As credenciais devem ser gerenciadas no backend
        bucket_name: alert.resource_id,
        region: alert.region,
      });
      // Atualizar a lista de alertas após a remediação
      handleAnalysis('aws', 's3', 'AWS S3 Buckets');
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message;
      setError(t('dashboardPage.errorDuringRemediation', { error: errorMessage }));
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalysis = async (provider: string, servicePath: string, currentAnalysisType: string) => {
    setIsLoading(true);
    setError(null);
    setAlerts([]);
    setAnalysisType(currentAnalysisType);

    try {
      const response = await apiClient.post<AlertType[]>(`/analyze/aws/${servicePath}`, {});
      setAlerts(response.data || []);
      if (response.data.length === 0) {
        setError(t('dashboardPage.noNewAlertsForAnalysis', { type: currentAnalysisType }));
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message;
      setError(t('dashboardPage.errorDuringAnalysis', { type: currentAnalysisType, provider: 'AWS', error: errorMessage }));
    } finally {
      setIsLoading(false);
    }
  };

  const providerConfig = {
    providerNameKey: 'dashboardPage.awsAnalysisTitle',
    analysisButtons: [
      { id: 's3', labelKey: 'dashboardPage.analyzeS3Button', servicePath: 's3', analysisType: 'AWS S3 Buckets' },
      { id: 'ec2Instances', labelKey: 'dashboardPage.analyzeEC2InstancesButton', servicePath: 'ec2/instances', analysisType: 'AWS EC2 Instances' },
      { id: 'ec2Sgs', labelKey: 'dashboardPage.analyzeEC2SGsButton', servicePath: 'ec2/security-groups', analysisType: 'AWS EC2 Security Groups' },
      { id: 'iamUsers', labelKey: 'dashboardPage.analyzeIAMUsersButton', servicePath: 'iam/users', analysisType: 'AWS IAM Users' },
      { id: 'rdsInstances', labelKey: 'dashboardPage.analyzeRDSInstancesButton', servicePath: 'rds/instances', analysisType: 'AWS RDS Instances' },
    ]
  };

  return (
    <div>
      <Title order={2} mb="xl">{t(providerConfig.providerNameKey, 'AWS Analysis')}</Title>

      <ProviderAnalysisSection
        providerId="aws"
        providerNameKey={providerConfig.providerNameKey}
        analysisButtons={providerConfig.analysisButtons}
        onAnalyze={handleAnalysis}
        isLoading={isLoading}
        currentAnalysisType={analysisType}
      />

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
          onRemediate={handleRemediation}
        />
      )}
    </div>
  );
};

export default AwsDashboardPage;
