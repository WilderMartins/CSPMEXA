import React from 'react';
import { useTranslation } from 'react-i18next';

// Simulação de componentes de uma biblioteca UI como Mantine
// Em um projeto real, seriam importados: import { Button, TextInput, Paper, Title, Group } from '@mantine/core';

const Paper: React.FC<{ children: React.ReactNode, padding?: string, shadow?: string, style?: React.CSSProperties }> = ({ children, style, ...props }) => (
  <div style={{ padding: props.padding || 'md', boxShadow: props.shadow ? `0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.1)` : 'none', border: '1px solid #e0e0e0', borderRadius: '5px', ...style }} {...props}>
    {children}
  </div>
);

const Title: React.FC<{ order?: 1 | 2 | 3 | 4 | 5 | 6, children: React.ReactNode, style?: React.CSSProperties }> = ({ order = 3, children, style }) => {
  const Tag = `h${order}` as keyof JSX.IntrinsicElements;
  return <Tag style={{ marginTop: 0, marginBottom: '1rem', ...style }}>{children}</Tag>;
};

const Button: React.FC<React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: string, style?: React.CSSProperties }> = ({ children, style, ...props }) => (
  <button
    style={{
      padding: '8px 16px',
      border: '1px solid #ccc',
      borderRadius: '4px',
      cursor: props.disabled ? 'not-allowed' : 'pointer',
      backgroundColor: props.disabled ? '#e9ecef' : (props.variant === 'light' ? '#f8f9fa' : '#007bff'),
      color: props.disabled ? '#adb5bd' : (props.variant === 'light' ? '#212529' : 'white'),
      ...style
    }}
    {...props}
  >
    {children}
  </button>
);

const TextInput: React.FC<React.InputHTMLAttributes<HTMLInputElement> & { label?: string, description?: string, style?: React.CSSProperties, inputStyle?: React.CSSProperties }> = ({ label, description, style, inputStyle, ...props }) => (
  <div style={{ marginBottom: '1rem', ...style }}>
    {label && <label htmlFor={props.id || props.name} style={{ display: 'block', marginBottom: '4px', fontSize: '0.9em', fontWeight: '500' }}>{label}</label>}
    <input
      type="text"
      style={{
        width: '100%',
        padding: '8px',
        border: '1px solid #ced4da',
        borderRadius: '4px',
        boxSizing: 'border-box',
        ...inputStyle
      }}
      {...props}
    />
    {description && <small style={{ display: 'block', marginTop: '4px', color: '#6c757d' }}>{description}</small>}
  </div>
);

const Group: React.FC<{ children: React.ReactNode, style?: React.CSSProperties, grow?: boolean }> = ({ children, style, grow }) => (
  <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'flex-end', ...style }}>
    {grow ? React.Children.map(children, child => React.isValidElement(child) ? React.cloneElement(child as React.ReactElement<any>, { style: { ...child.props.style, flexGrow: 1 } }) : child) : children}
  </div>
);


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
    <Paper padding="lg" shadow="xs" style={{ marginBottom: '2rem' }}>
      <Title order={2} style={{ marginBottom: '1.5rem' }}>{t(providerNameKey)}</Title>

      {inputFields.length > 0 && (
        <Group grow style={{ marginBottom: '1.5rem' }}>
          {inputFields.map(field => (
            <TextInput
              key={field.id}
              id={field.id}
              label={t(field.labelKey)}
              placeholder={t(field.placeholderKey)}
              value={field.value}
              onChange={(e) => field.setter(e.target.value)}
              type={field.type || 'text'}
              disabled={isLoading}
            />
          ))}
        </Group>
      )}

      <Title order={4} style={{ marginBottom: '1rem' }}>{t('dashboardPage.analysisActions')}</Title>
      <Group>
        {analysisButtons.map((button) => (
          <Button
            key={button.id}
            onClick={() => handleAnalysisClick(button)}
            disabled={isLoading || !areAllParamsFilled(button.requiredParams)}
            variant="light"
          >
            {isLoading && currentAnalysisType === button.analysisType
              ? t('dashboardPage.analyzingButton')
              : t(button.labelKey)}
          </Button>
        ))}
      </Group>
    </Paper>
  );
};

export default ProviderAnalysisSection;
