import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AlertsTable, { Alert } from './AlertsTable'; // Ajuste o caminho se necessário

const mockAlerts: Alert[] = [
  { id: 1, resource_id: 'bucket-1', resource_type: 'S3 Bucket', provider: 'AWS', severity: 'Critical', title: 'S3 Public Access', description: 'Bucket is public', policy_id: 'S3-001', status: 'Open', created_at: '2023-01-01T10:00:00Z', updated_at: '2023-01-01T10:00:00Z', first_seen_at: '2023-01-01T10:00:00Z', last_seen_at: '2023-01-01T10:00:00Z', details: { acl: 'public' }, recommendation: 'Make private' },
  { id: 2, resource_id: 'instance-1', resource_type: 'EC2 Instance', provider: 'AWS', severity: 'High', title: 'Unrestricted SSH', description: 'SSH open to 0.0.0.0/0', policy_id: 'EC2-002', status: 'Open', created_at: '2023-01-02T10:00:00Z', updated_at: '2023-01-02T10:00:00Z', first_seen_at: '2023-01-02T10:00:00Z', last_seen_at: '2023-01-02T10:00:00Z' },
  { id: 3, resource_id: 'vm-abc', resource_type: 'VM Instance', provider: 'GCP', severity: 'Medium', title: 'Default Service Account', description: 'VM uses default SA', policy_id: 'GCP-VM-001', status: 'Closed', created_at: '2023-01-03T10:00:00Z', updated_at: '2023-01-03T10:00:00Z', first_seen_at: '2023-01-03T10:00:00Z', last_seen_at: '2023-01-03T10:00:00Z' },
  { id: 4, resource_id: 'storage-xyz', resource_type: 'Storage Account', provider: 'Azure', severity: 'Low', title: 'Public Blob Access', description: 'Public access enabled', policy_id: 'AZ-STR-005', status: 'Open', created_at: '2023-01-04T10:00:00Z', updated_at: '2023-01-04T10:00:00Z', first_seen_at: '2023-01-04T10:00:00Z', last_seen_at: '2023-01-04T10:00:00Z' },
  // Adicionar mais 7 alertas para testar paginação (total 11)
  { id: 5, resource_id: 'obs-bucket-5', resource_type: 'OBS Bucket', provider: 'Huawei', severity: 'Critical', title: 'OBS Public', description: 'OBS public', policy_id: 'HW-OBS-001', status: 'Open', created_at: '2023-01-05T10:00:00Z', updated_at: '2023-01-05T10:00:00Z', first_seen_at: '2023-01-05T10:00:00Z', last_seen_at: '2023-01-05T10:00:00Z' },
  { id: 6, resource_id: 'user-6', resource_type: 'IAM User', provider: 'AWS', severity: 'High', title: 'Inactive Keys', description: 'Access keys not used', policy_id: 'IAM-003', status: 'Open', created_at: '2023-01-06T10:00:00Z', updated_at: '2023-01-06T10:00:00Z', first_seen_at: '2023-01-06T10:00:00Z', last_seen_at: '2023-01-06T10:00:00Z' },
  { id: 7, resource_id: 'project-iam-7', resource_type: 'Project IAM', provider: 'GCP', severity: 'Critical', title: 'External Owner', description: 'External user is owner', policy_id: 'GCP-IAM-001', status: 'Closed', created_at: '2023-01-07T10:00:00Z', updated_at: '2023-01-07T10:00:00Z', first_seen_at: '2023-01-07T10:00:00Z', last_seen_at: '2023-01-07T10:00:00Z' },
  { id: 8, resource_id: 'vm-8', resource_type: 'Virtual Machine', provider: 'Azure', severity: 'Medium', title: 'Missing Endpoint Protection', description: 'No AV installed', policy_id: 'AZ-VM-002', status: 'Open', created_at: '2023-01-08T10:00:00Z', updated_at: '2023-01-08T10:00:00Z', first_seen_at: '2023-01-08T10:00:00Z', last_seen_at: '2023-01-08T10:00:00Z' },
  { id: 9, resource_id: 'ecs-9', resource_type: 'ECS Instance', provider: 'Huawei', severity: 'High', title: 'Public IP', description: 'ECS has public IP', policy_id: 'HW-ECS-002', status: 'Open', created_at: '2023-01-09T10:00:00Z', updated_at: '2023-01-09T10:00:00Z', first_seen_at: '2023-01-09T10:00:00Z', last_seen_at: '2023-01-09T10:00:00Z' },
  { id: 10, resource_id: 's3-bucket-10', resource_type: 'S3 Bucket', provider: 'AWS', severity: 'Low', title: 'No Versioning', description: 'Versioning disabled', policy_id: 'S3-003', status: 'Open', created_at: '2023-01-10T10:00:00Z', updated_at: '2023-01-10T10:00:00Z', first_seen_at: '2023-01-10T10:00:00Z', last_seen_at: '2023-01-10T10:00:00Z' },
  { id: 11, resource_id: 'drive-11', resource_type: 'Shared Drive', provider: 'GoogleWorkspace', severity: 'Medium', title: 'Publicly Shared Drive', description: 'Shared drive is public.', policy_id: 'GWS-DRV-001', status: 'Open', created_at: '2023-01-11T10:00:00Z', updated_at: '2023-01-11T10:00:00Z', first_seen_at: '2023-01-11T10:00:00Z', last_seen_at: '2023-01-11T10:00:00Z' },
];

const tableTitle = "Test Alerts";

describe('AlertsTable Component', () => {
  beforeEach(() => {
    // O mock de i18next já está no setupTests.ts
  });

  it('renders alerts correctly and shows the title', () => {
    render(<AlertsTable alerts={mockAlerts.slice(0, 3)} title={tableTitle} />);
    expect(screen.getByText(tableTitle)).toBeInTheDocument();
    expect(screen.getByText('S3 Public Access')).toBeInTheDocument();
    expect(screen.getByText('Unrestricted SSH')).toBeInTheDocument();
    expect(screen.getByText('Default Service Account')).toBeInTheDocument();
  });

  it('filters alerts by severity', () => {
    render(<AlertsTable alerts={mockAlerts} title={tableTitle} />);
    // userEvent é melhor para interações de usuário, mas fireEvent é mais simples para select
    fireEvent.change(screen.getByLabelText('alertFilters.severity:'), { target: { value: 'Critical' } });
    expect(screen.getByText('S3 Public Access')).toBeInTheDocument(); // AWS Critical
    expect(screen.getByText('OBS Public')).toBeInTheDocument(); // Huawei Critical
    expect(screen.getByText('External Owner')).toBeInTheDocument(); // GCP Critical
    expect(screen.queryByText('Unrestricted SSH')).not.toBeInTheDocument(); // AWS High
  });

  it('filters alerts by provider', () => {
    render(<AlertsTable alerts={mockAlerts} title={tableTitle} />);
    fireEvent.change(screen.getByLabelText('alertFilters.provider:'), { target: { value: 'GCP' } });
    expect(screen.getByText('Default Service Account')).toBeInTheDocument(); // GCP Medium
    expect(screen.getByText('External Owner')).toBeInTheDocument(); // GCP Critical
    expect(screen.queryByText('S3 Public Access')).not.toBeInTheDocument(); // AWS
  });

  it('filters alerts by status', () => {
    render(<AlertsTable alerts={mockAlerts} title={tableTitle} />);
    fireEvent.change(screen.getByLabelText('alertFilters.status:'), { target: { value: 'Closed' } });
    expect(screen.getByText('Default Service Account')).toBeInTheDocument(); // GCP Medium, Closed
    expect(screen.getByText('External Owner')).toBeInTheDocument(); // GCP Critical, Closed
    expect(screen.queryByText('S3 Public Access')).not.toBeInTheDocument(); // AWS Critical, Open
  });

  it('sorts alerts by ID (ascending and descending)', () => {
    render(<AlertsTable alerts={mockAlerts.slice(0,3)} title={tableTitle} />);
    const idHeader = screen.getByText('alertItem.id');

    // Ascending
    userEvent.click(idHeader);
    let rows = screen.getAllByRole('row'); // Inclui header row
    // rows[1] é a primeira linha de dados
    expect(rows[1].cells[0]).toHaveTextContent('1'); // ID 1
    expect(rows[2].cells[0]).toHaveTextContent('2'); // ID 2
    expect(rows[3].cells[0]).toHaveTextContent('3'); // ID 3

    // Descending
    userEvent.click(idHeader);
    rows = screen.getAllByRole('row');
    expect(rows[1].cells[0]).toHaveTextContent('3');
    expect(rows[2].cells[0]).toHaveTextContent('2');
    expect(rows[3].cells[0]).toHaveTextContent('1');
  });

  it('sorts alerts by Severity (ascending and descending - assumes alphabetical for simplicity)', () => {
    render(<AlertsTable alerts={mockAlerts.slice(0,4)} title={tableTitle} />); // Critical, High, Medium, Low
    const severityHeader = screen.getByText('alertItem.severity');

    // Ascending (Critical, High, Low, Medium - alphabetical)
    userEvent.click(severityHeader);
    let rows = screen.getAllByRole('row');
    expect(rows[1].cells[2]).toHaveTextContent('Critical');
    expect(rows[2].cells[2]).toHaveTextContent('High');
    expect(rows[3].cells[2]).toHaveTextContent('Low');
    expect(rows[4].cells[2]).toHaveTextContent('Medium');

    // Descending (Medium, Low, High, Critical - reverse alphabetical)
    userEvent.click(severityHeader);
    rows = screen.getAllByRole('row');
    expect(rows[1].cells[2]).toHaveTextContent('Medium');
    expect(rows[2].cells[2]).toHaveTextContent('Low');
    expect(rows[3].cells[2]).toHaveTextContent('High');
    expect(rows[4].cells[2]).toHaveTextContent('Critical');
  });


  it('handles pagination correctly', () => {
    render(<AlertsTable alerts={mockAlerts} title={tableTitle} />); // 11 alerts, 10 per page
    expect(screen.getByText('S3 Public Access')).toBeInTheDocument(); // Alerta 1
    expect(screen.queryByText('Publicly Shared Drive')).not.toBeInTheDocument(); // Alerta 11 (na próxima página)
    expect(screen.getByText('pagination.page', { currentPage: 1, totalPages: 2 })).toBeInTheDocument();

    const nextButton = screen.getByText('pagination.next');
    userEvent.click(nextButton);

    expect(screen.queryByText('S3 Public Access')).not.toBeInTheDocument();
    expect(screen.getByText('Publicly Shared Drive')).toBeInTheDocument(); // Alerta 11
    expect(screen.getByText('pagination.page', { currentPage: 2, totalPages: 2 })).toBeInTheDocument();

    const prevButton = screen.getByText('pagination.previous');
    userEvent.click(prevButton);
    expect(screen.getByText('S3 Public Access')).toBeInTheDocument();
  });

  it('opens and closes the details modal on row click', () => {
    render(<AlertsTable alerts={mockAlerts} title={tableTitle} />);

    // Modal não deve estar visível inicialmente
    expect(screen.queryByText('alertDetails.title')).not.toBeInTheDocument();

    // Clica na primeira linha de dados (o alerta com título "S3 Public Access")
    const firstDataRow = screen.getByText('S3 Public Access').closest('tr');
    expect(firstDataRow).toBeInTheDocument();
    if(firstDataRow) userEvent.click(firstDataRow);

    // Modal deve estar visível
    expect(screen.getByText('alertDetails.title')).toBeInTheDocument();
    expect(screen.getByText('Bucket is public')).toBeInTheDocument(); // Description do alerta 1
    expect(screen.getByText(JSON.stringify({ acl: 'public' }, null, 2))).toBeInTheDocument(); // Details
    expect(screen.getByText('Make private')).toBeInTheDocument(); // Recommendation

    // Fecha o modal
    // O botão de fechar é um "✕"
    const closeButton = screen.getByText('✕');
    userEvent.click(closeButton);
    expect(screen.queryByText('alertDetails.title')).not.toBeInTheDocument();
  });

  it('shows "no alerts" message when alerts array is empty or null', () => {
    const { rerender } = render(<AlertsTable alerts={[]} title={tableTitle} />);
    expect(screen.getByText('dashboardPage.noAlertsToDisplay')).toBeInTheDocument();

    // @ts-ignore para testar o caso de null, embora a prop espere Alert[]
    rerender(<AlertsTable alerts={null as any} title={tableTitle} />);
    expect(screen.getByText('dashboardPage.noAlertsToDisplay')).toBeInTheDocument();
  });

});
