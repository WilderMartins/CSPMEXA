import React from 'react';
import { render, screen } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import AttackPathsDisplay from './AttackPathsDisplay'; // Ajuste o caminho
import { AttackPath } from '../../services/reportsService'; // Ajuste o caminho

const mockPaths: AttackPath[] = [
  {
    id: 'ap-001',
    description: 'Public EC2 to Sensitive S3',
    path: [
      { resourceId: 'ec2-instance-123', resourceType: 'EC2 Instance', vulnerability: 'Publicly Exposed, Unrestricted SG' },
      { resourceId: 's3-bucket-789', resourceType: 'S3 Bucket', vulnerability: 'Readable by Instance Role' }
    ],
    severity: 'High'
  },
  {
    id: 'ap-002',
    description: 'Compromised User to Admin Role',
    path: [
      { resourceId: 'user-xyz', resourceType: 'IAM User', vulnerability: 'Leaked Credentials' },
      { resourceId: 'admin-role', resourceType: 'IAM Role', vulnerability: 'Assumable by User' }
    ],
    severity: 'Medium'
  },
];

const renderWithMantine = (ui: React.ReactElement) => {
  return render(<MantineProvider>{ui}</MantineProvider>);
};

describe('AttackPathsDisplay Component', () => {
  it('renders loading message when isLoading is true', () => {
    renderWithMantine(<AttackPathsDisplay paths={[]} isLoading={true} error={null} />);
    expect(screen.getByText('insightsPage.loadingAttackPaths', { exact: false })).toBeInTheDocument();
  });

  it('renders error message when error is present', () => {
    renderWithMantine(<AttackPathsDisplay paths={[]} isLoading={false} error="Failed to fetch paths" />);
    expect(screen.getByText(/Error loading attack paths: Failed to fetch paths/i)).toBeInTheDocument();
  });

  it('renders "no paths" message when paths array is empty and not loading', () => {
    renderWithMantine(<AttackPathsDisplay paths={[]} isLoading={false} error={null} />);
    expect(screen.getByText('insightsPage.noAttackPaths', { exact: false })).toBeInTheDocument();
  });

  it('renders a list of attack paths correctly', () => {
    renderWithMantine(<AttackPathsDisplay paths={mockPaths} isLoading={false} error={null} />);

    // Path 1
    expect(screen.getByText((content, el) => content.includes('Path ID: ap-001') && content.includes('High'))).toBeInTheDocument();
    expect(screen.getByText((content, el) => content.startsWith('insightsPage.attackPathDescription') && content.includes('Public EC2 to Sensitive S3'))).toBeInTheDocument();
    expect(screen.getByText(/EC2 Instance \(ec2-instance-123\): Publicly Exposed, Unrestricted SG/i)).toBeInTheDocument();
    expect(screen.getByText(/S3 Bucket \(s3-bucket-789\): Readable by Instance Role/i)).toBeInTheDocument();

    // Path 2
    expect(screen.getByText((content, el) => content.includes('Path ID: ap-002') && content.includes('Medium'))).toBeInTheDocument();
    expect(screen.getByText((content, el) => content.startsWith('insightsPage.attackPathDescription') && content.includes('Compromised User to Admin Role'))).toBeInTheDocument();
    expect(screen.getByText(/IAM User \(user-xyz\): Leaked Credentials/i)).toBeInTheDocument();
    expect(screen.getByText(/IAM Role \(admin-role\): Assumable by User/i)).toBeInTheDocument();
  });

  it('applies correct color styling for path severity', () => {
    renderWithMantine(<AttackPathsDisplay paths={mockPaths} isLoading={false} error={null} />);

    // Path 1: Severity High (espera cor vermelha)
    const highSeverityPath = screen.getByText('High');
    expect(highSeverityPath).toHaveStyle('color: var(--mantine-color-red-7)');

    // Path 2: Severity Medium (espera cor laranja)
    const mediumSeverityPath = screen.getByText('Medium');
    expect(mediumSeverityPath).toHaveStyle('color: var(--mantine-color-orange-7)');
  });
});
