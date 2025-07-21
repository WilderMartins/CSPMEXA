import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import ProviderAnalysisSection from './ProviderAnalysisSection'; // Ajuste o caminho se necessário

// Mock de i18next já está em setupTests.ts
// const mockT = (key: string, params?: any) => params ? `${key}_${JSON.stringify(params)}` : key;
// jest.mock('react-i18next', () => ({
//   useTranslation: () => ({ t: mockT }),
// }));

const mockOnAnalyze = jest.fn();

const defaultProps = {
  providerNameKey: 'dashboardPage.awsAnalysisTitle',
  providerId: 'aws' as 'aws' | 'gcp' | 'huawei' | 'azure' | 'googleworkspace',
  inputFields: [
    { id: 'awsAccountId', labelKey: 'aws.accountIdLabel', placeholderKey: 'aws.accountIdPlaceholder', value: '', setter: jest.fn(), type: 'text' as 'text' | 'email' },
    { id: 'awsRegion', labelKey: 'aws.regionLabel', placeholderKey: 'aws.regionPlaceholder', value: '', setter: jest.fn(), type: 'text' as 'text' | 'email' },
  ],
  analysisButtons: [
    { id: 's3', labelKey: 'dashboardPage.analyzeS3Button', servicePath: 's3', analysisType: 'AWS S3', requiredParams: ['awsAccountId', 'awsRegion'] },
    { id: 'ec2', labelKey: 'dashboardPage.analyzeEC2Button', servicePath: 'ec2', analysisType: 'AWS EC2', requiredParams: [] }, // Sem params obrigatórios
  ],
  onAnalyze: mockOnAnalyze,
  isLoading: false,
  currentAnalysisType: null,
};

// Envolver com MantineProvider para que os componentes Mantine funcionem corretamente nos testes
const renderWithMantine = (ui: React.ReactElement) => {
  return render(<MantineProvider>{ui}</MantineProvider>);
};

describe('ProviderAnalysisSection Component', () => {
  beforeEach(() => {
    mockOnAnalyze.mockClear();
    // Resetar os setters dos inputFields se eles forem modificados nos testes
    defaultProps.inputFields.forEach(field => field.setter.mockClear());
    defaultProps.inputFields[0].value = ''; // Limpar valor para cada teste
    defaultProps.inputFields[1].value = ''; // Limpar valor para cada teste
  });

  it('renders the provider title, input fields, and analysis buttons', () => {
    renderWithMantine(<ProviderAnalysisSection {...defaultProps} />);

    expect(screen.getByText('dashboardPage.awsAnalysisTitle')).toBeInTheDocument();

    // Verifica inputs
    expect(screen.getByLabelText('aws.accountIdLabel')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('aws.accountIdPlaceholder')).toBeInTheDocument();
    expect(screen.getByLabelText('aws.regionLabel')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('aws.regionPlaceholder')).toBeInTheDocument();

    // Verifica botões
    expect(screen.getByRole('button', { name: 'dashboardPage.analyzeS3Button' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'dashboardPage.analyzeEC2Button' })).toBeInTheDocument();
  });

  it('calls setter function when an input field is changed', async () => {
    const mockSetterAccount = jest.fn();
    const propsWithMockSetter = {
      ...defaultProps,
      inputFields: [
        { ...defaultProps.inputFields[0], value: '', setter: mockSetterAccount },
        defaultProps.inputFields[1],
      ],
    };
    renderWithMantine(<ProviderAnalysisSection {...propsWithMockSetter} />);

    const accountIdInput = screen.getByLabelText('aws.accountIdLabel');
    await userEvent.type(accountIdInput, '12345');

    expect(mockSetterAccount).toHaveBeenCalledWith('1');
    expect(mockSetterAccount).toHaveBeenCalledWith('12');
    expect(mockSetterAccount).toHaveBeenCalledWith('123');
    expect(mockSetterAccount).toHaveBeenCalledWith('1234');
    expect(mockSetterAccount).toHaveBeenCalledWith('12345');
  });

  it('calls onAnalyze with correct parameters when an analysis button is clicked', async () => {
    // Para este teste, vamos simular que os inputs têm valores
    const currentInputValues: Record<string, string> = {
      awsAccountId: 'test-account-id',
      awsRegion: 'us-east-1',
    };

    const propsWithValues = {
      ...defaultProps,
      inputFields: defaultProps.inputFields.map(field => ({
        ...field,
        // Simula que o valor do input é controlado externamente e passado via prop 'value'
        // e que o setter atualizaria esse valor no componente pai.
        // Nos testes, precisamos garantir que o 'value' passado para onAnalyze reflita o que deveria ser o estado atual.
        // O mock de 'setter' não altera 'value' diretamente aqui, então passamos manualmente.
        value: currentInputValues[field.id] || '',
      })),
    };

    renderWithMantine(<ProviderAnalysisSection {...propsWithValues} />);

    const s3Button = screen.getByRole('button', { name: 'dashboardPage.analyzeS3Button' });
    await userEvent.click(s3Button);

    expect(mockOnAnalyze).toHaveBeenCalledTimes(1);
    expect(mockOnAnalyze).toHaveBeenCalledWith(
      'aws', // providerId
      's3',  // servicePath
      'AWS S3', // analysisType
      // Os parâmetros passados para onAnalyze devem ser os valores dos inputs
      // que são requeridos pelo botão S3.
      {
        awsAccountId: 'test-account-id',
        awsRegion: 'us-east-1'
        // Adicionar 'domainId' se fosse um botão que o requeresse e estivesse nos inputFields
      }
    );
  });

  it('disables analysis button if required params are not filled', () => {
    // Props onde os inputFields estão vazios
    const propsWithEmptyInputs = {
        ...defaultProps,
        inputFields: defaultProps.inputFields.map(field => ({...field, value: ''}))
    };
    renderWithMantine(<ProviderAnalysisSection {...propsWithEmptyInputs} />);

    const s3Button = screen.getByRole('button', { name: 'dashboardPage.analyzeS3Button' });
    // O botão S3 requer awsAccountId e awsRegion, que estão vazios
    expect(s3Button).toBeDisabled();

    const ec2Button = screen.getByRole('button', { name: 'dashboardPage.analyzeEC2Button' });
    // O botão EC2 não tem requiredParams, então não deve estar desabilitado por falta de params
    expect(ec2Button).not.toBeDisabled();
  });

  it('shows loading state on button when isLoading is true and currentAnalysisType matches', () => {
    renderWithMantine(
      <ProviderAnalysisSection
        {...defaultProps}
        isLoading={true}
        currentAnalysisType={'AWS S3'}
      />
    );

    const s3Button = screen.getByRole('button', { name: 'dashboardPage.analyzeS3Button' });
    // O Mantine Button mostra um loader quando a prop 'loading' é true.
    // A prop 'loading' no botão é (isLoading && currentAnalysisType === button.analysisType)
    // O texto do botão não muda, mas ele entra em estado de loading.
    // Testing Library não tem um matcher direto para "isLoading" de Mantine,
    // mas podemos verificar se ele está desabilitado (Mantine desabilita botões em loading).
    expect(s3Button).toBeDisabled();
    // Poderíamos também adicionar um data-testid ao loader dentro do botão Mantine se quiséssemos ser mais específicos,
    // mas isso exigiria modificar o componente Mantine ou sua implementação interna.

    const ec2Button = screen.getByRole('button', { name: 'dashboardPage.analyzeEC2Button' });
    // Este botão não deve estar em loading
    expect(ec2Button).not.toBeDisabled();
  });

});
