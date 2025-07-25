import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Table, Button, Modal, Pagination, Group, Text, UnstyledButton, Center, rem, Stack, Box, Select } from '@mantine/core';
import { IconSelector, IconChevronDown, IconChevronUp } from '@tabler/icons-react'; // Ícones para ordenação
import ReactMarkdown from 'react-markdown';
import AlertsTableFilters from './AlertsTableFilters';

// Componente para o cabeçalho da tabela ordenável
interface ThProps {
  children: React.ReactNode;
  reversed: boolean;
  sorted: boolean;
  onSort(): void;
  width?: string | number;
}

function Th({ children, reversed, sorted, onSort, width }: ThProps) {
  const Icon = sorted ? (reversed ? IconChevronUp : IconChevronDown) : IconSelector;
  return (
    <Table.Th style={{ width }}>
      <UnstyledButton onClick={onSort} style={{width: '100%'}}>
        <Group justify="space-between" gap="xs" wrap="nowrap">
          <Text fw={500} fz="sm">
            {children}
          </Text>
          <Center>
            <Icon style={{ width: rem(16), height: rem(16) }} stroke={1.5} />
          </Center>
        </Group>
      </UnstyledButton>
    </Table.Th>
  );
}

export interface Alert {
  id: number;
  resource_id: string;
  resource_type: string;
  account_id?: string;
  region?: string;
  provider: string;
  severity: string;
  title: string;
  description: string;
  policy_id: string;
  status: string;
  details?: Record<string, any>;
  recommendation?: string;
  remediation_guide?: string;
  created_at: string;
  updated_at: string;
  first_seen_at: string;
  last_seen_at: string;
}

type SortableColumn = 'id' | 'provider' | 'severity' | 'status' | 'first_seen_at' | 'last_seen_at';

interface AlertsTableProps {
  alerts: Alert[];
  title: string;
  onUpdateStatus: (alertId: number, newStatus: string) => Promise<void>;
  canUpdateStatus: boolean;
  onRemediate?: (alert: Alert) => Promise<void>;
}

const ITEMS_PER_PAGE = 10;

const AlertsTable: React.FC<AlertsTableProps> = ({ alerts, title, onUpdateStatus, canUpdateStatus, onRemediate }) => {
  const { t } = useTranslation();
  const [currentPage, setCurrentPage] = useState(1);
  const [sortColumn, setSortColumn] = useState<SortableColumn>('last_seen_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const [filterSeverity, setFilterSeverity] = useState<string | null>('');
  const [filterProvider, setFilterProvider] = useState<string | null>('');
  const [filterStatus, setFilterStatus] = useState<string | null>(null);

  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const uniqueSeverities = useMemo(() => Array.from(new Set(alerts.map(a => a.severity))), [alerts]);
  const uniqueProviders = useMemo(() => Array.from(new Set(alerts.map(a => a.provider))), [alerts]);
  const uniqueStatuses = useMemo(() => Array.from(new Set(alerts.map(a => a.status))), [alerts]);

  const filteredAlerts = useMemo(() => {
    return alerts.filter(alert => {
      return (filterSeverity ? alert.severity === filterSeverity : true) &&
             (filterProvider ? alert.provider === filterProvider : true) &&
             (filterStatus ? alert.status === filterStatus : true);
    });
  }, [alerts, filterSeverity, filterProvider, filterStatus]);

  const sortedData = useMemo(() => {
    const data = [...filteredAlerts];
    if (!sortColumn) return data;

    return data.sort((a, b) => {
      let valA = a[sortColumn];
      let valB = b[sortColumn];

      if (sortColumn === 'id') {
        valA = Number(valA);
        valB = Number(valB);
      } else if (['first_seen_at', 'last_seen_at'].includes(sortColumn)) {
        valA = new Date(valA as string).getTime();
        valB = new Date(valB as string).getTime();
      } else if (typeof valA === 'string' && typeof valB === 'string') {
        valA = valA.toLowerCase();
        valB = valB.toLowerCase();
      }

      if (sortDirection === 'asc') {
        return valA < valB ? -1 : valA > valB ? 1 : 0;
      }
      return valB < valA ? -1 : valB > valA ? 1 : 0;
    });
  }, [filteredAlerts, sortColumn, sortDirection]);

  const paginatedAlerts = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    return sortedData.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [sortedData, currentPage]);

  const totalPages = Math.ceil(sortedData.length / ITEMS_PER_PAGE);

  const handleSort = (column: SortableColumn) => {
    if (sortColumn === column) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const getSeverityStyle = (severity: string): React.CSSProperties => {
    let color = 'var(--mantine-color-text)';
    let finalFontWeight: 'normal' | 'bold' = 'normal';

    switch (severity.toLowerCase()) {
      case 'critical': color = 'var(--mantine-color-red-7)'; finalFontWeight = 'bold'; break;
      case 'high': color = 'var(--mantine-color-orange-7)'; finalFontWeight = 'bold'; break;
      case 'medium': color = 'var(--mantine-color-yellow-7)'; break;
      case 'low': color = 'var(--mantine-color-blue-7)'; break;
      case 'informational': color = 'var(--mantine-color-gray-7)'; break;
    }
    return { color, fontWeight: finalFontWeight };
  };

  const handleRowClick = (alert: Alert) => {
    setSelectedAlert(alert);
    setIsModalOpen(true);
  };

  if (!alerts) {
    return <Text>{t('dashboardPage.noAlertsToDisplay', 'No alerts to display.')}</Text>;
  }
  if (alerts.length === 0 && !filterSeverity && !filterProvider && !filterStatus) {
    return <Text>{t('dashboardPage.noAlertsToDisplay', 'No alerts to display.')}</Text>;
  }

  const rows = paginatedAlerts.map((alert) => (
    <Table.Tr key={alert.id} onClick={() => handleRowClick(alert)} style={{cursor: 'pointer'}}>
      <Table.Td>{alert.id}</Table.Td>
      <Table.Td>{alert.provider.toUpperCase()}</Table.Td>
      <Table.Td><Text component="span" style={getSeverityStyle(alert.severity)}>{alert.severity}</Text></Table.Td>
      <Table.Td title={alert.description}>{alert.title}</Table.Td>
      <Table.Td>{alert.resource_id}</Table.Td>
      <Table.Td>{alert.resource_type}</Table.Td>
      <Table.Td>{alert.status}</Table.Td>
      <Table.Td>{new Date(alert.first_seen_at).toLocaleString()}</Table.Td>
      <Table.Td>{new Date(alert.last_seen_at).toLocaleString()}</Table.Td>
    </Table.Tr>
  ));

  const handleFilterChange = (setter: (value: string | null) => void) => (value: string | null) => {
    setter(value);
    setCurrentPage(1);
  };

  return (
    <div style={{ marginTop: rem(32) }}>
      <Text component="h3" size="lg" fw={600} mb="md">{title}</Text>

      <AlertsTableFilters
        filterSeverity={filterSeverity}
        setFilterSeverity={handleFilterChange(setFilterSeverity)}
        uniqueSeverities={uniqueSeverities}
        filterProvider={filterProvider}
        setFilterProvider={handleFilterChange(setFilterProvider)}
        uniqueProviders={uniqueProviders}
        filterStatus={filterStatus}
        setFilterStatus={handleFilterChange(setFilterStatus)}
        uniqueStatuses={uniqueStatuses}
      />

      {paginatedAlerts.length > 0 ? (
        <Table.ScrollContainer minWidth={800}>
          <Table highlightOnHover withTableBorder withColumnBorders verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Th sorted={sortColumn === 'id'} reversed={sortDirection === 'desc'} onSort={() => handleSort('id')} width="5%">{t('alertItem.id')}</Th>
                <Th sorted={sortColumn === 'provider'} reversed={sortDirection === 'desc'} onSort={() => handleSort('provider')} width="10%">{t('alertItem.provider')}</Th>
                <Th sorted={sortColumn === 'severity'} reversed={sortDirection === 'desc'} onSort={() => handleSort('severity')} width="10%">{t('alertItem.severity')}</Th>
                <Table.Th>{t('alertItem.title')}</Table.Th>
                <Table.Th>{t('alertItem.resource')}</Table.Th>
                <Table.Th>{t('alertItem.resourceType')}</Table.Th>
                <Th sorted={sortColumn === 'status'} reversed={sortDirection === 'desc'} onSort={() => handleSort('status')} width="10%">{t('alertItem.status')}</Th>
                <Th sorted={sortColumn === 'first_seen_at'} reversed={sortDirection === 'desc'} onSort={() => handleSort('first_seen_at')} width="15%">{t('alertItem.firstSeen')}</Th>
                <Th sorted={sortColumn === 'last_seen_at'} reversed={sortDirection === 'desc'} onSort={() => handleSort('last_seen_at')} width="15%">{t('alertItem.lastSeen')}</Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>{rows}</Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      ) : (
        <Text mt="md">{t('alertsTable.noMatchingAlerts', 'No alerts match the current filters.')}</Text>
      )}

      {totalPages > 1 && (
        <Group justify="flex-end" mt="md">
          <Pagination total={totalPages} value={currentPage} onChange={setCurrentPage} />
        </Group>
      )}

      <Modal
        opened={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={t('alertDetails.title', 'Alert Details')}
        size="lg"
        overlayProps={{
          backgroundOpacity: 0.55,
          blur: 3,
        }}
      >
        {selectedAlert && (
          <Stack gap="sm">
            <Text><strong>{t('alertItem.id')}:</strong> {selectedAlert.id}</Text>
            <Text><strong>{t('alertItem.title')}:</strong> {selectedAlert.title}</Text>
            <Text><strong>{t('alertItem.provider')}:</strong> {selectedAlert.provider.toUpperCase()}</Text>
            <Text>
              <strong>{t('alertItem.severity')}:</strong> <Text component="span" c={getSeverityStyle(selectedAlert.severity).color} fw={getSeverityStyle(selectedAlert.severity).fontWeight === 'bold' ? 700 : 400}>{selectedAlert.severity}</Text>
            </Text>

            {canUpdateStatus ? (
              <Select
                label={t('alertItem.status')}
                value={selectedAlert.status}
                onChange={async (newStatus) => {
                  if (newStatus && newStatus !== selectedAlert.status) {
                    await onUpdateStatus(selectedAlert.id, newStatus);
                    setSelectedAlert(prev => prev ? { ...prev, status: newStatus } : null);
                  }
                }}
                data={[
                  { value: 'OPEN', label: t('alertStatus.OPEN', 'Open') },
                  { value: 'ACKNOWLEDGED', label: t('alertStatus.ACKNOWLEDGED', 'Acknowledged') },
                  { value: 'RESOLVED', label: t('alertStatus.RESOLVED', 'Resolved') },
                  { value: 'IGNORED', label: t('alertStatus.IGNORED', 'Ignored') },
                ]}
                disabled={!canUpdateStatus}
                mb="sm"
              />
            ) : (
              <Text><strong>{t('alertItem.status')}:</strong> {selectedAlert.status}</Text>
            )}

            <Text><strong>{t('alertItem.resource')}:</strong> {selectedAlert.resource_id}</Text>
            <Text><strong>{t('alertItem.resourceType')}:</strong> {selectedAlert.resource_type}</Text>
            {selectedAlert.account_id && <Text><strong>{t('alertItem.accountId')}:</strong> {selectedAlert.account_id}</Text>}
            {selectedAlert.region && <Text><strong>{t('alertItem.region')}:</strong> {selectedAlert.region}</Text>}
            <Text><strong>{t('alertItem.description')}:</strong> {selectedAlert.description}</Text>
            {selectedAlert.recommendation && <Text><strong>{t('alertItem.recommendation')}:</strong> {selectedAlert.recommendation}</Text>}
            {selectedAlert.remediation_guide && (
              <div>
                <Text fw={500}>{t('alertItem.remediationGuide')}:</Text>
                <Box p="xs" style={{ backgroundColor: 'var(--mantine-color-gray-0)', borderRadius: '4px', border: '1px solid var(--mantine-color-gray-3)' }}>
                  <ReactMarkdown>{selectedAlert.remediation_guide}</ReactMarkdown>
                </Box>
                <Button
                  mt="sm"
                  size="xs"
                  color="teal"
                  onClick={() => onRemediate && onRemediate(selectedAlert)}
                  disabled={!onRemediate}
                >
                  Remediar
                </Button>
              </div>
            )}
            <Text><strong>{t('alertItem.policyId')}:</strong> {selectedAlert.policy_id}</Text>
            <Text><strong>{t('alertItem.firstSeen')}:</strong> {new Date(selectedAlert.first_seen_at).toLocaleString()}</Text>
            <Text><strong>{t('alertItem.lastSeen')}:</strong> {new Date(selectedAlert.last_seen_at).toLocaleString()}</Text>
            {selectedAlert.details && (
              <div>
                <Text fw={500}>{t('alertItem.details')}:</Text>
                <pre style={{ backgroundColor: 'var(--mantine-color-gray-1)', padding: '10px', borderRadius: '4px', whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: '0.85em' }}>
                  {JSON.stringify(selectedAlert.details, null, 2)}
                </pre>
              </div>
            )}
          </Stack>
        )}
      </Modal>
    </div>
  );
};

export default AlertsTable;
