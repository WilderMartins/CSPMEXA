import React from 'react';
import { useTranslation } from 'react-i18next';
import { Button, TextInput, Paper, Title, Group, Stack } from '@mantine/core'; // Importar da Mantine

interface AnalysisButton {
  id: string;
  labelKey: string; // Chave para tradução do t()
  servicePath: string;
  analysisType: string; // Para o estado currentAnalysisType
  requiredParams?: string[]; // Nomes dos parâmetros de ID necessários (ex: 'projectId')
}

interface InputField {
  id: string;
  labelKey: string;
  placeholderKey: string;
  value: string;
  setter: (value: string) => void;
  type?: 'text' | 'email';
}

interface ProviderAnalysisSectionProps {
  providerNameKey: string; // Chave para o título da seção (ex: 'dashboardPage.awsAnalysisTitle')
  providerId: 'aws' | 'gcp' | 'huawei' | 'azure' | 'googleworkspace';
  inputFields?: InputField[];
  analysisButtons: AnalysisButton[];
  onAnalyze: (
    provider: 'aws' | 'gcp' | 'huawei' | 'azure' | 'googleworkspace',
    servicePath: string,
    analysisType: string,
    idParams?: Record<string, string | undefined>
  ) => void;
  isLoading: boolean;
  currentAnalysisType: string | null;
}

const ProviderAnalysisSection: React.FC<ProviderAnalysisSectionProps> = ({
  providerNameKey,
  providerId,
  inputFields = [],
  analysisButtons,
  onAnalyze,
  isLoading,
  currentAnalysisType,
}) => {
  const { t } = useTranslation();

  const handleAnalysisClick = (button: AnalysisButton) => {
    const params: Record<string, string | undefined> = {};
    if (button.requiredParams) {
      for (const paramName of button.requiredParams) {
        const field = inputFields.find(f => f.id === paramName);
        if (field) {
          params[paramName] = field.value;
        } else {
          // Fallback para IDs específicos se não estiverem nos inputFields genéricos
          // (ex: domainId para Huawei IAM users, que pode não ser um inputField padrão)
          // Esta lógica pode precisar de ajuste dependendo de como os IDs são gerenciados
          if (paramName === 'domainId' && providerId === 'huawei') {
             const domainField = inputFields.find(f => f.id === 'huaweiDomainId');
             if (domainField) params.domainId = domainField.value;
          }
        }
      }
    }
    onAnalyze(providerId, button.servicePath, button.analysisType, params);
  };

  const areAllParamsFilled = (requiredParams?: string[]): boolean => {
    if (!requiredParams || requiredParams.length === 0) return true;
    return requiredParams.every(paramName => {
      const field = inputFields.find(f => f.id === paramName);
      // Para Huawei IAM, projectId pode ser opcional, mas regionId não.
      // Esta lógica de validação pode precisar ser mais granular ou movida para a `DashboardPage`.
      if (providerId === 'huawei' && button.servicePath === 'iam/users' && paramName === 'projectId') {
        return true; // projectId é opcional para Huawei IAM Users
      }
      return field && field.value.trim() !== '';
    });
  };

  return (
    // Mantine Paper já tem margem padrão, mas podemos adicionar mb (margin-bottom) se necessário com props de estilo
    <Paper p="lg" shadow="xs" radius="md" withBorder mb="xl">
      <Title order={2} mb="xl">{t(providerNameKey)}</Title>

      {inputFields.length > 0 && (
        // Usar Stack para empilhar os TextInputs verticalmente
        // Ou Group com direction="column" dependendo do layout desejado.
        // Se os inputs devem crescer para preencher a largura, Group com grow pode ser usado,
        // mas para múltiplos inputs empilhados, Stack é mais direto.
        // Para inputs lado a lado, Group é ideal. Vamos assumir que eles podem ficar empilhados.
        <Stack mb="xl">
          {inputFields.map(field => (
            <TextInput
              key={field.id}
              id={field.id}
              label={t(field.labelKey)}
              placeholder={t(field.placeholderKey)}
              value={field.value}
              onChange={(e) => field.setter(e.currentTarget.value)} // Mantine usa currentTarget
              type={field.type || 'text'}
              disabled={isLoading}
              // style={{ flexGrow: 1 }} // Se dentro de um Group com grow
            />
          ))}
        </Stack>
      )}

      <Title order={4} mb="md">{t('dashboardPage.analysisActions')}</Title>
      <Group>
        {analysisButtons.map((button) => (
          <Button
            key={button.id}
            onClick={() => handleAnalysisClick(button)}
            disabled={!areAllParamsFilled(button.requiredParams)} // isLoading é tratado pela prop loading
            loading={isLoading && currentAnalysisType === button.analysisType}
            variant="light" // Mantine tem variantes como 'filled', 'light', 'outline', 'default'
          >
            {t(button.labelKey)}
            {/* O texto do botão não precisa mais mudar para 'Analisando...' pois o Mantine Button tem um loader embutido */}
          </Button>
        ))}
      </Group>
    </Paper>
  );
};

export default ProviderAnalysisSection;
