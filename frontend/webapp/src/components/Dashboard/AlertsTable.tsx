import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';

// --- Simulação de Componentes UI ---
// Estes seriam importados de uma biblioteca de UI em um projeto real.

/** @private Botão simulado para UI. */
const Button: React.FC<React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: string, size?: string, style?: React.CSSProperties }> = ({ children, variant = 'default', size = 'md', style, ...props }) => (
  <button
    style={{
      padding: size === 'sm' ? '4px 8px' : '8px 16px',
      fontSize: size === 'sm' ? '0.8rem' : '1rem',
      border: '1px solid #ccc',
      borderRadius: '4px',
      cursor: props.disabled ? 'not-allowed' : 'pointer',
      backgroundColor: props.disabled ? '#e9ecef' : (variant === 'light' ? '#f8f9fa' : '#007bff'),
      color: props.disabled ? '#adb5bd' : (variant === 'light' ? '#212529' : 'white'),
      ...style
    }}
    {...props}
  >
    {children}
  </button>
);

/** @private Componente Select simulado para UI. */
const Select: React.FC<React.SelectHTMLAttributes<HTMLSelectElement> & { label?: string, data: Array<{value: string, label: string}>, style?: React.CSSProperties }> = ({ label, data, style, ...props }) => (
  <div style={{ display: 'inline-block', marginRight: '10px', marginBottom: '10px', ...style }}>
    {label && <label style={{ marginRight: '5px', fontSize: '0.9em' }}>{label}:</label>}
    <select
      style={{ padding: '6px', borderRadius: '4px', border: '1px solid #ccc' }}
      {...props}
    >
      {data.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
    </select>
  </div>
);

/** @private Componente Modal simulado para UI. */
const Modal: React.FC<{ opened: boolean, onClose: () => void, title: string, children: React.ReactNode }> = ({ opened, onClose, title, children }) => {
  if (!opened) return null;
  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '5px', minWidth: '300px', maxWidth: '80%', maxHeight: '80%', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h3 style={{ margin: 0 }}>{title}</h3>
          <Button onClick={onClose} variant="light" size="sm" style={{backgroundColor: 'transparent', border: 'none', fontSize: '1.2rem', color: '#555'}}>✕</Button>
        </div>
        {children}
      </div>
    </div>
  );
};

/**
 * Representa a estrutura de um objeto de Alerta.
 * Esta interface é usada tanto pelo `AlertsTable` quanto pelo `DashboardPage`.
 */
export interface Alert {
  /** Identificador numérico único do alerta. */
  id: number;
  /** Identificador do recurso ao qual o alerta se refere. */
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
  created_at: string;
  updated_at: string;
  first_seen_at: string;
  last_seen_at: string;
}

/**
 * Define as colunas que podem ser usadas para ordenação na tabela de alertas.
 */
type SortableColumn = 'id' | 'provider' | 'severity' | 'status' | 'first_seen_at' | 'last_seen_at';

/**
 * Props para o componente {@link AlertsTable}.
 */
interface AlertsTableProps {
  /** Uma lista de objetos de Alerta a serem exibidos na tabela. */
  alerts: Alert[];
  /** O título a ser exibido acima da tabela de alertas. */
  title: string;
}

const ITEMS_PER_PAGE = 10;

/**
 * `AlertsTable` é um componente React que renderiza uma tabela de alertas
 * com funcionalidades de filtragem, ordenação e paginação.
 * Também inclui um modal para visualização detalhada de cada alerta.
 *
 * @component
 * @example
 * const myAlerts = [{id: 1, ...}, {id: 2, ...}];
 * return <AlertsTable alerts={myAlerts} title="Meus Alertas Atuais" />
 */
const AlertsTable: React.FC<AlertsTableProps> = ({ alerts, title }) => {
  const { t } = useTranslation();
  const [currentPage, setCurrentPage] = useState(1);
  const [sortColumn, setSortColumn] = useState<SortableColumn>('last_seen_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const [filterSeverity, setFilterSeverity] = useState<string>('');
  const [filterProvider, setFilterProvider] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');

  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

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

  const sortedAlerts = useMemo(() => {
    return [...filteredAlerts].sort((a, b) => {
      let valA = a[sortColumn];
      let valB = b[sortColumn];

      if (sortColumn === 'id') { // Assuming ID is number
        valA = Number(valA);
        valB = Number(valB);
      } else if (['first_seen_at', 'last_seen_at'].includes(sortColumn)) {
        valA = new Date(valA as string).getTime();
        valB = new Date(valB as string).getTime();
      } else if (typeof valA === 'string' && typeof valB === 'string') {
        valA = valA.toLowerCase();
        valB = valB.toLowerCase();
      }

      if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
      if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredAlerts, sortColumn, sortDirection]);

  const paginatedAlerts = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    return sortedAlerts.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [sortedAlerts, currentPage]);

  const totalPages = Math.ceil(sortedAlerts.length / ITEMS_PER_PAGE);

  const handleSort = (column: SortableColumn) => {
    if (sortColumn === column) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const renderSortArrow = (column: SortableColumn) => {
    if (sortColumn === column) {
      return sortDirection === 'asc' ? ' ▲' : ' ▼';
    }
    return '';
  };

  const tableHeaderStyle: React.CSSProperties = {
    border: '1px solid #ddd', padding: '10px', textAlign: 'left', backgroundColor: '#f8f9fa', fontWeight: 600, cursor: 'pointer'
  };
  const tableCellStyle: React.CSSProperties = { border: '1px solid #ddd', padding: '10px', textAlign: 'left' };
  const evenRowStyle: React.CSSProperties = { backgroundColor: '#ffffff' };
  const oddRowStyle: React.CSSProperties = { backgroundColor: '#f9f9f9' };

  const getSeverityStyle = (severity: string): React.CSSProperties => {
    let color = '#212529'; let fontWeight: 'normal' | 'bold' = 'normal';
    switch (severity.toLowerCase()) {
      case 'critical': color = '#dc3545'; fontWeight = 'bold'; break;
      case 'high': color = '#fd7e14'; fontWeight = 'bold'; break;
      case 'medium': color = '#ffc107'; break;
      case 'low': color = '#17a2b8'; break;
      case 'informational': color = '#6c757d'; break;
    }
    return { ...tableCellStyle, color, fontWeight };
  };

  if (!alerts || alerts.length === 0) {
    return <p>{t('dashboardPage.noAlertsToDisplay')}</p>;
  }

  return (
    <div className="alerts-table-container" style={{ marginTop: '2rem' }}>
      <h3 style={{ marginBottom: '1rem' }}>{title}</h3>

      <div className="filters" style={{ marginBottom: '1rem' }}>
        <Select
          label={t('alertFilters.severity')}
          value={filterSeverity}
          onChange={(e) => { setFilterSeverity(e.target.value); setCurrentPage(1); }}
          data={[{ value: '', label: t('alertFilters.allSeverities') }, ...uniqueSeverities.map(s => ({ value: s, label: s }))]}
        />
        <Select
          label={t('alertFilters.provider')}
          value={filterProvider}
          onChange={(e) => { setFilterProvider(e.target.value); setCurrentPage(1); }}
          data={[{ value: '', label: t('alertFilters.allProviders') }, ...uniqueProviders.map(p => ({ value: p, label: p.toUpperCase() }))]}
        />
        <Select
          label={t('alertFilters.status')}
          value={filterStatus}
          onChange={(e) => { setFilterStatus(e.target.value); setCurrentPage(1); }}
          data={[{ value: '', label: t('alertFilters.allStatuses') }, ...uniqueStatuses.map(s => ({ value: s, label: s }))]}
        />
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9em' }}>
        <thead>
          <tr>
            {([
              { key: 'id', label: t('alertItem.id') },
              { key: 'provider', label: t('alertItem.provider') },
              { key: 'severity', label: t('alertItem.severity') },
              { key: 'title', label: t('alertItem.title'), sortable: false },
              { key: 'resource', label: t('alertItem.resource'), sortable: false },
              { key: 'resourceType', label: t('alertItem.resourceType'), sortable: false },
              { key: 'status', label: t('alertItem.status') },
              { key: 'first_seen_at', label: t('alertItem.firstSeen') },
              { key: 'last_seen_at', label: t('alertItem.lastSeen') },
            ] as Array<{key: SortableColumn | string, label: string, sortable?: boolean}>).map(col => (
              <th
                key={col.key}
                style={{...tableHeaderStyle, cursor: (col.sortable !== false) ? 'pointer' : 'default'}}
                onClick={() => (col.sortable !== false) && handleSort(col.key as SortableColumn)}
              >
                {col.label}
                {(col.sortable !== false) && renderSortArrow(col.key as SortableColumn)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {paginatedAlerts.map((alert, index) => (
            <tr
              key={alert.id}
              style={index % 2 === 0 ? evenRowStyle : oddRowStyle}
              onClick={() => setSelectedAlert(alert)}
              title={t('alertsTable.clickToViewDetails')}
              role="button"
              tabIndex={0}
              onKeyPress={(e) => e.key === 'Enter' && setSelectedAlert(alert)}
              style={{ cursor: 'pointer', ...(index % 2 === 0 ? evenRowStyle : oddRowStyle) }}
            >
              <td style={tableCellStyle}>{alert.id}</td>
              <td style={tableCellStyle}>{alert.provider.toUpperCase()}</td>
              <td style={getSeverityStyle(alert.severity)}>{alert.severity}</td>
              <td style={tableCellStyle} title={alert.description}>{alert.title}</td>
              <td style={tableCellStyle}>{alert.resource_id}</td>
              <td style={tableCellStyle}>{alert.resource_type}</td>
              <td style={tableCellStyle}>{alert.status}</td>
              <td style={tableCellStyle}>{new Date(alert.first_seen_at).toLocaleString()}</td>
              <td style={tableCellStyle}>{new Date(alert.last_seen_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {totalPages > 1 && (
        <div className="pagination" style={{ marginTop: '1rem', textAlign: 'right' }}>
          <Button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1} variant="light" size="sm" style={{marginRight: '5px'}}>
            {t('pagination.previous')}
          </Button>
          <span style={{margin: '0 10px', fontSize: '0.9em'}}>
            {t('pagination.page', { currentPage, totalPages })}
          </span>
          <Button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages} variant="light" size="sm">
            {t('pagination.next')}
          </Button>
        </div>
      )}

      <Modal
        opened={!!selectedAlert}
        onClose={() => setSelectedAlert(null)}
        title={t('alertDetails.title')}
      >
        {selectedAlert && (
          <div>
            <p><strong>{t('alertItem.id')}:</strong> {selectedAlert.id}</p>
            <p><strong>{t('alertItem.title')}:</strong> {selectedAlert.title}</p>
            <p><strong>{t('alertItem.provider')}:</strong> {selectedAlert.provider.toUpperCase()}</p>
            <p><strong>{t('alertItem.severity')}:</strong> {selectedAlert.severity}</p>
            <p><strong>{t('alertItem.status')}:</strong> {selectedAlert.status}</p>
            <p><strong>{t('alertItem.resource')}:</strong> {selectedAlert.resource_id}</p>
            <p><strong>{t('alertItem.resourceType')}:</strong> {selectedAlert.resource_type}</p>
            {selectedAlert.account_id && <p><strong>{t('alertItem.accountId')}:</strong> {selectedAlert.account_id}</p>}
            {selectedAlert.region && <p><strong>{t('alertItem.region')}:</strong> {selectedAlert.region}</p>}
            <p><strong>{t('alertItem.description')}:</strong> {selectedAlert.description}</p>
            {selectedAlert.recommendation && <p><strong>{t('alertItem.recommendation')}:</strong> {selectedAlert.recommendation}</p>}
            <p><strong>{t('alertItem.policyId')}:</strong> {selectedAlert.policy_id}</p>
            <p><strong>{t('alertItem.firstSeen')}:</strong> {new Date(selectedAlert.first_seen_at).toLocaleString()}</p>
            <p><strong>{t('alertItem.lastSeen')}:</strong> {new Date(selectedAlert.last_seen_at).toLocaleString()}</p>
            {selectedAlert.details && (
              <div>
                <strong>{t('alertItem.details')}:</strong>
                <pre style={{ backgroundColor: '#f0f0f0', padding: '10px', borderRadius: '4px', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                  {JSON.stringify(selectedAlert.details, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default AlertsTable;
